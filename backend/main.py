# -*- coding: utf-8 -*-
# backend/main.py

from ai import find_best_move, LLMError
from game import OmokGame
import os
import uuid
import traceback
from typing import Dict, Optional
from threading import Lock
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect  # [PvP] WebSocket 추가
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pathlib import Path
from dotenv import load_dotenv
from starlette.websockets import WebSocketState  # [PvP] 상태 체크용

load_dotenv(dotenv_path=Path(__file__).with_name(".env"), override=True)

OMOK_LLM_URL = os.getenv("OMOK_LLM_URL", "http://127.0.0.1:8001/omok/move")
print("OMOK_LLM_URL =", OMOK_LLM_URL)

_game_locks = defaultdict(Lock)
def _get_lock(game_id: str) -> Lock:
    return _game_locks[game_id]

load_dotenv(override=True)

app = FastAPI(title="Omok Backend", version="3.1.0")  # [CHANGE] 버전 올림

# [IMPROVE] CORS 설정을 환경 변수에서 읽어오도록 변경하여 유연성 확보
CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ORIGINS_STR.split(",")]
print("ALLOWED_ORIGINS =", ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # [IMPROVE] WebSocket 및 향후 인증을 위해 True로 설정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ───────────── 전역 예외 핸들러(디버그) ─────────────
@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print("\n[EXC]", exc.__class__.__name__, exc, "\n", tb)
    return JSONResponse(status_code=500, content={"detail": str(exc)})

# ───────────── 메모리 저장 ─────────────
games: Dict[str, OmokGame] = {}

# [PvP] 각 게임의 WS 슬롯(흑/백) 관리
connections: Dict[str, Dict[str, Optional[WebSocket]]] = {}  # {"game_id": {"black": ws|None, "white": ws|None}}

# ───────────── 유틸(승리 판정 포함) ─────────────
DIRS = ((1, 0), (0, 1), (1, 1), (1, -1))

def _moves_with_players(g: OmokGame):
    """OmokGame.moves -> [{"x":..,"y":..,"player":..,"move_no":..}] 로 변환"""
    hist = []
    turn = 1  # 게임 시작은 흑(1)
    for idx, (x,y) in enumerate(getattr(g, "moves", []), start=1):
        hist.append({"x": int(x), "y": int(y), "player": turn, "move_no": idx})
        turn = 2 if turn == 1 else 1
    return hist

def _normalize_difficulty(v: str) -> str:
    """프론트에서 무엇이 오든 '초급' 또는 '고급' 둘 중 하나로 정규화."""
    if not v:
        return "초급"
    t = str(v).strip().lower()
    if t in ("고급", "hard", "advanced", "pro"):
        return "고급"
    # 그 외(easy, beginner 등)는 모두 초급 취급
    return "초급"

def _in_bounds(board, y, x):
    return 0 <= y < len(board) and 0 <= x < len(board[0])

def _count_line(board, y, x, dy, dx, who):
    cnt = 0
    ny, nx = y + dy, x + dx
    while _in_bounds(board, ny, nx) and board[ny][nx] == who:
        cnt += 1
        ny += dy
        nx += dx
    return cnt

def _is_five_or_more(board, y, x, who):
    for dy, dx in DIRS:
        c = 1
        c += _count_line(board, y, x, dy, dx, who)
        c += _count_line(board, y, x, -dy, -dx, who)
        if c >= 5:
            return True
    return False

def _get_game_or_404(game_id: str) -> OmokGame:
    g = games.get(game_id)
    if g is None:
        raise HTTPException(status_code=404, detail="게임을 찾을 수 없습니다.")
    return g

def _try_call_any(obj, name, *args, **kwargs):
    fn = getattr(obj, name, None)
    if callable(fn):
        return True, fn(*args, **kwargs)
    return False, None

# [PvP] 서버 표준 상태 페이로드(프론트 호환: game_over 포함)
def _state(g: OmokGame, game_id: str, message: str = "") -> dict:
    state = {
        "game_id": game_id,
        "board": g.board,
        "current_turn": getattr(g, "current_turn", 1),
        "game_over": bool(getattr(g, "winner", None) is not None),  # [PvP] 추가
        "winner": getattr(g, "winner", None),
    }
    if message:
        state["message"] = message
    return state

# [PvP] WS 브로드캐스트
async def _broadcast(game_id: str, payload: dict):
    conns = connections.get(game_id) or {}
    for role in ("black", "white"):
        ws = conns.get(role)
        if ws and ws.application_state == WebSocketState.CONNECTED:
            try:
                await ws.send_json(payload)
            except Exception:
                pass

# ───────────── [AI-Assist] 유틸 추가 ─────────────
def _swap_board_colors(board):  # [AI-Assist] 1↔2 스왑 (흑 추천용)
    return [[0 if v == 0 else (2 if v == 1 else 1) for v in row] for row in board]

def _first_playable_black(g: OmokGame):  # [AI-Assist] 흑 금수 회피 간단 폴백
    n = len(g.board)
    # 인접 빈칸 우선
    def has_neighbor(x, y):
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if dx==0 and dy==0: continue
                yy, xx = y+dy, x+dx
                if 0<=yy<n and 0<=xx<n and g.board[yy][xx]!=0:
                    return True
        return False
    coords = [(x,y) for y in range(n) for x in range(n) if g.board[y][x]==0 and has_neighbor(x,y)]
    if not coords:
        coords = [(x,y) for y in range(n) for x in range(n) if g.board[y][x]==0]
    cx = cy = n//2
    coords.sort(key=lambda p: max(abs(p[0]-cx), abs(p[1]-cy)))  # 중심 가까운 순
    # 금수 회피
    for x,y in coords:
        if hasattr(g, "_is_forbidden_move"):
            bad, _ = g._is_forbidden_move(x, y)
            if bad: 
                continue
        return (x, y)
    return None

# ───────────── 스키마 ─────────────
class NewGameResponse(BaseModel):
    id: str
    game_id: str                       # [CHANGE] 프론트 호환을 위해 추가(=id)
    board: list
    winner: Optional[int] = None
    current_turn: Optional[int] = None
    game_over: Optional[bool] = None   # [CHANGE] 추가
    player_color: Optional[int] = None # [PvP] 방만든 사람은 흑(1)

class MoveRequest(BaseModel):
    x: int
    y: int
    player: Optional[int] = None  # [CHANGE] 선택값으로—서버에서 무시하고 현재 턴 사용

class MoveResponse(BaseModel):
    x: int
    y: int
    board: list
    winner: Optional[int] = None
    current_turn: Optional[int] = None
    game_over: Optional[bool] = None   # [CHANGE] 추가
    message: Optional[str] = None      # [CHANGE] 금수/안내 메시지

class DifficultyRequest(BaseModel):
    difficulty: str = Field(..., description="초급 | 고급")

class GameStateResponse(BaseModel):
    id: str
    game_id: str                       # [CHANGE] 추가(=id)
    board: list
    winner: Optional[int] = None
    current_turn: Optional[int] = None
    game_over: Optional[bool] = None   # [CHANGE] 추가

# ───────────── [AI-Assist] 스키마 추가 ──────────────────────────
class AssistRequest(BaseModel):  # [AI-Assist] 수정됨
    player: int | None = None          # 내 색(1=흑, 2=백). 생략 시 현재 서버 턴
    difficulty: str | None = None      # "초급"/"고급" (생략시 고급 추천)

class AssistResponse(BaseModel):  # [AI-Assist] 수정됨
    x: int
    y: int
    player: int
    source: str | None = None
    message: str | None = None

# ───────────── 라우트 ─────────────
@app.get("/__ping__")
def ping():
    return {"ok": True}

# [CHANGE] 새게임: 기존 응답을 유지하면서 PvP 정보(id=game_id, player_color=1, game_over)도 같이 반환
@app.post("/api/game/new", response_model=NewGameResponse)
def new_game():
    gid = str(uuid.uuid4())
    g = OmokGame()  # 상대방 엔진 그대로 사용
    games[gid] = g
    # [PvP] 슬롯 준비
    connections[gid] = {"black": None, "white": None}
    return {
        "id": gid,
        "game_id": gid,                              # [CHANGE]
        "board": g.board,
        "winner": g.winner,
        "current_turn": getattr(g, "current_turn", 1),
        "game_over": bool(g.winner is not None),     # [CHANGE]
        "player_color": 1,                           # [PvP] 방장은 흑
    }

# [PvP] 방 참가 (빈 슬롯 배정)
@app.post("/api/game/{game_id}/join")
def join_game(game_id: str):
    _get_game_or_404(game_id)   # 존재 확인
    conns = connections[game_id]  # ensure init
    if conns["black"] is None:
        return {"game_id": game_id, "player_color": 1}
    elif conns["white"] is None:
        return {"game_id": game_id, "player_color": 2}
    else:
        return {"error": "이미 두 명이 참가 중입니다."}

@app.get("/api/game/{game_id}", response_model=GameStateResponse)
def get_game(game_id: str):
    g = _get_game_or_404(game_id)
    return {
        "id": game_id,
        "game_id": game_id,                          # [CHANGE]
        "board": g.board,
        "winner": g.winner,
        "current_turn": getattr(g, "current_turn", 1),
        "game_over": bool(g.winner is not None),     # [CHANGE]
    }

# [CHANGE] 수 두기: 요청의 player를 신뢰하지 않고, 서버 현재 턴을 사용
@app.post("/api/game/{game_id}/move", response_model=MoveResponse)
async def place_move(game_id: str, req: MoveRequest):                     # ★ 수정됨 (async)
    g = _get_game_or_404(game_id)
    if g.winner is not None:
        raise HTTPException(status_code=400, detail="이미 종료된 게임입니다.")
    x, y = int(req.x), int(req.y)
    server_player = int(getattr(g, "current_turn", 1))  # 서버에서 결정

    ok, msg = g.place_stone(x, y, server_player)
    if not ok:
        raise HTTPException(status_code=400, detail=str(msg or "유효하지 않은 수입니다."))

    resp = {
        "x": x,
        "y": y,
        "board": g.board,
        "winner": g.winner,
        "current_turn": getattr(g, "current_turn", 1),
        "game_over": bool(g.winner is not None),
        "message": msg or "돌을 놓았습니다.",
    }

    # ★ 수정됨: PvP 브로드캐스트(양쪽 보드 동기화)
    try:
        await _broadcast(game_id, { "type": "game_update", "payload": _state(g, game_id) })
    except Exception:
        pass

    return resp

# ───────────── AI (상대 방식을 유지) ─────────────
@app.post("/api/game/{game_id}/ai-move", response_model=MoveResponse)
async def ai_move(game_id: str, req: DifficultyRequest):                 # ★ 수정됨 (async)
    g = _get_game_or_404(game_id)
    lock = _get_lock(game_id)

    with lock:
        if g.winner is not None:
            raise HTTPException(status_code=400, detail="이미 종료된 게임입니다.")

        diff = _normalize_difficulty(getattr(req, "difficulty", None))
        print(f"[ai-move] received={req.difficulty!r} -> normalized={diff}")
        history = _moves_with_players(g)
        try:
            move = find_best_move(g.board, diff, history=history)
        except LLMError as e:
            raise HTTPException(status_code=503, detail=f"AI(LLM) 사용 불가: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI 내부 오류: {e!r}")

        x, y = int(move["x"]), int(move["y"])
        ok, msg = g.place_stone(x, y, 2)
        if not ok:
            raise HTTPException(status_code=500, detail="AI가 유효하지 않은 좌표를 반환했습니다.")

    try:
        print(f"[APPLY AI] (x={x}, y={y}) -> board[y][x]=2")
        if hasattr(g, "print_board"):
            g.print_board()
    except Exception:
        pass

    # ★ 수정됨: AI 수 역시 브로드캐스트(관전자/상대 화면 즉시 반영)
    try:
        await _broadcast(game_id, { "type": "game_update", "payload": _state(g, game_id) })
    except Exception:
        pass

    return {
        "x": x,
        "y": y,
        "board": g.board,
        "winner": g.winner,
        "current_turn": getattr(g, "current_turn", 1),
        "game_over": bool(g.winner is not None),
        "message": msg or "AI 착수",
    }

# ───────────── WebSocket (PvP 채팅/시스템 메세지) ─────────────
@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    if game_id not in games:
        await websocket.close()
        return

    conns = connections.setdefault(game_id, {"black": None, "white": None})

    if conns["black"] is None:
        conns["black"] = websocket
        me = 1
    elif conns["white"] is None:
        conns["white"] = websocket
        me = 2
    else:
        await websocket.close()
        return

    await websocket.send_json({
        "type": "system",
        "payload": {
            "message": f"게임에 참가했습니다. 당신의 돌은 {'흑' if me == 1 else '백'}입니다.",
            "player_color": me
        }
    })

    # ★ 수정됨: 입장과 동시에 현재 보드 상태를 싱크
    try:
        await websocket.send_json({ "type": "game_update", "payload": _state(games[game_id], game_id) })
    except Exception:
        pass

    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "chat_message":
                await _broadcast(game_id, {
                    "type": "chat_message",
                    "payload": { "sender": "흑" if me == 1 else "백", "message": data["payload"]["message"] }
                })
    except WebSocketDisconnect:
        if conns.get("black") is websocket:
            conns["black"] = None
        elif conns.get("white") is websocket:
            conns["white"] = None

# ───────────── [AI-Assist] 추천 좌표 엔드포인트 ─────────────
@app.post("/api/game/{game_id}/assist", response_model=AssistResponse)
def assist_move(game_id: str, req: AssistRequest):
    """
    내 차례에 AI가 '추천 좌표'만 알려주는 API.
    - pvai: 사람=흑(1) 기준 추천
    - pvp : 각자 자신의 color 기준 추천
    - 흑 추천은 금수(장목/3-3/4-4) 반드시 회피
    """
    g = _get_game_or_404(game_id)
    if g.winner is not None:
        raise HTTPException(status_code=400, detail="이미 종료된 게임입니다.")

    # 내 색 결정(요청이 없으면 현재 턴)
    player = int(req.player or getattr(g, "current_turn", 1))
    diff = _normalize_difficulty(req.difficulty or "고급")

    # 진행 로그는 ai.py가 흰(2) 기준일 때만 넘김 (흑은 보드 스왑을 하므로 생략)
    history = _moves_with_players(g) if player == 2 else None

    try:
        if player == 2:
            # 백 추천: 그대로 호출
            mv = find_best_move(g.board, diff, history=history)
            x, y = int(mv["x"]), int(mv["y"])
            # 유효성
            if not (0 <= y < len(g.board) and 0 <= x < len(g.board[0])) or g.board[y][x] != 0:
                raise HTTPException(status_code=500, detail="추천 좌표가 잘못되었습니다(백).")
            return {"x": x, "y": y, "player": 2, "source": "ai(white)", "message": "추천 수(백)"}
        else:
            # 흑 추천: 보드 색을 1↔2 스왑한 뒤 '백' 알고리즘을 호출
            inv = _swap_board_colors(g.board)
            mv = find_best_move(inv, diff, history=None)
            x, y = int(mv["x"]), int(mv["y"])
            # 유효성 + 흑 금수 회피
            if not (0 <= y < len(g.board) and 0 <= x < len(g.board[0])) or g.board[y][x] != 0:
                # 폴백
                best = _first_playable_black(g)
                if not best:
                    raise HTTPException(status_code=500, detail="추천 좌표를 찾지 못했습니다(흑).")
                x, y = best
            if hasattr(g, "_is_forbidden_move"):
                bad, why = g._is_forbidden_move(x, y)
                if bad:
                    # 간단 폴백으로 금수 회피
                    best = _first_playable_black(g)
                    if best:
                        x, y = best
                    else:
                        raise HTTPException(status_code=400, detail=f"추천 결과가 금수입니다({why}).")
            return {"x": x, "y": y, "player": 1, "source": "ai(black, swapped)", "message": "추천 수(흑)"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 실패: {e!r}")

# ───────────── 기존 코드 유지 ─────────────
