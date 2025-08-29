# -*- coding: utf-8 -*-
# backend/llm_server.py
from __future__ import annotations
import os, json, re
from typing import List, Tuple, Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OMOK_LLM_KEY")
OPENAI_MODEL   = os.getenv("OMOK_LLM_MODEL", "gpt-4.1")
DEBUG          = os.getenv("OMOK_LLM_DEBUG", "0") == "1"
PROMPT_LOG_MODE = os.getenv("OMOK_LLM_DEBUG_PROMPT", "lite").lower()

BOARD_SIZE       = int(os.getenv("OMOK_BOARD_SIZE", "15"))
N_CANDS          = int(os.getenv("OMOK_LLM_N_CANDS", "3"))
CAND_MIN_DIST    = int(os.getenv("OMOK_CAND_MIN_DIST", "2"))     # 체비쇼프 최소 거리
HISTORY_MAX      = int(os.getenv("OMOK_HISTORY_MAX", "16"))      # 최근 16수만 모델에 전달
MAX_TOKENS       = int(os.getenv("OMOK_LLM_MAX_TOKENS", "700"))
RETRY_MAX_TOKENS = int(os.getenv("OMOK_LLM_RETRY_MAX_TOKENS", "1200"))

if BOARD_SIZE < 5 or BOARD_SIZE > 25:
    raise RuntimeError("OMOK_BOARD_SIZE는 5~25 사이의 정수여야 합니다.")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 또는 OMOK_LLM_KEY가 필요합니다.")
client = OpenAI(api_key=OPENAI_API_KEY)

print("✅ Using model:", OPENAI_MODEL)
print("✅ Debug mode:", DEBUG)
print(f"✅ BOARD_SIZE: {BOARD_SIZE}×{BOARD_SIZE}")

app = FastAPI(title="Omok LLM Server", version="1.5.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"],
)

# ── 모델 I/O 스키마 ────────────────────────────────────────────────────
class Candidate(BaseModel):
    x: int
    y: int
    llm_score: float

class HistoryMove(BaseModel):
    x: int
    y: int
    player: int  # 1=흑, 2=백
    move_no: Optional[int] = None

class OmokMoveReq(BaseModel):
    board: List[List[int]] = Field(..., description=f"{BOARD_SIZE}x{BOARD_SIZE}, 0/1/2")
    difficulty: str = Field(..., description="초급/고급")
    player: int = Field(2, description="AI stone: 2(white)")
    history: Optional[List[HistoryMove]] = None

    @field_validator("board")
    @classmethod
    def _validate_board(cls, v: List[List[int]]):
        if not isinstance(v, list) or len(v) != BOARD_SIZE:
            raise ValueError(f"board는 {BOARD_SIZE}행이어야 합니다.")
        for row in v:
            if not isinstance(row, list) or len(row) != BOARD_SIZE:
                raise ValueError(f"board는 {BOARD_SIZE}x{BOARD_SIZE} 이어야 합니다.")
            for cell in row:
                if cell not in (0,1,2):
                    raise ValueError("board의 값은 0/1/2만 허용됩니다.")
        return v

class OmokMoveRes(BaseModel):
    x: int
    y: int
    player: int = 2
    candidates: Optional[List[Candidate]] = None
    debug_model: Optional[str] = None
    server: Optional[str] = None

# ── JSON Schema (슬림) ────────────────────────────────────────────────
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["x", "y", "candidates"],
    "properties": {
        "x": {"type": "integer"},
        "y": {"type": "integer"},
        "candidates": {
            "type": "array",
            "minItems": 1,
            "maxItems": N_CANDS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["x", "y", "llm_score"],
                "properties": {
                    "x": {"type": "integer"},
                    "y": {"type": "integer"},
                    "llm_score": {"type": "number"}
                }
            }
        }
    }
}

# ── 안전 파서 ─────────────────────────────────────────────────────────
def _safe_json_loads(s: str) -> dict:
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        s2 = s.strip()
        if s2.startswith("```"):  # 코드펜스 제거
            s2 = re.sub(r"^```(?:json)?", "", s2).strip()
            if s2.endswith("```"):
                s2 = s2[:-3].strip()
        i, j = s2.find("{"), s2.rfind("}")
        if i != -1 and j != -1 and j > i:
            s2 = s2[i:j+1]
        s2 = re.sub(r",(\s*[}\]])", r"\1", s2)  # 트레일링 콤마 제거
        s2 = s2.replace("NaN","0").replace("Infinity","0").replace("-Infinity","0")
        return json.loads(s2)

# ── 유틸 ───────────────────────────────────────────────────────────────
def _board_from_history(size:int, hist: Optional[List[HistoryMove]]) -> List[List[int]]:
    b = [[0]*size for _ in range(size)]
    if not hist:
        return b
    for mv in hist:
        if 0 <= mv.y < size and 0 <= mv.x < size:
            b[mv.y][mv.x] = mv.player
    return b

def _diff_coords(b1: List[List[int]], b2: List[List[int]]) -> List[Tuple[int,int,int,int]]:
    diffs=[]; n=len(b1)
    for y in range(n):
        for x in range(n):
            if b1[y][x] != b2[y][x]:
                diffs.append((x,y,b1[y][x],b2[y][x]))
    return diffs

def _diversify_candidates(cands: List[Candidate], n_keep: int, min_d: int) -> List[Candidate]:
    if not cands:
        return cands
    kept: List[Candidate] = []
    def cheb(a: Candidate, b: Candidate) -> int:
        return max(abs(a.x - b.x), abs(a.y - b.y))
    cands = sorted(cands, key=lambda c: float(getattr(c, "llm_score", 0.0)), reverse=True)
    for c in cands:
        if all(cheb(c, k) > min_d for k in kept):
            kept.append(c)
            if len(kept) >= n_keep:
                break
    if len(kept) < n_keep:
        for c in cands:
            if c not in kept:
                kept.append(c)
                if len(kept) >= n_keep:
                    break
    return kept

def _format_board(board: List[List[int]]) -> str:
    return "\n".join(" ".join(str(v) for v in row) for row in board)

def _find_first_empty(board: List[List[int]]) -> Optional[Tuple[int,int]]:
    for y,row in enumerate(board):
        for x,v in enumerate(row):
            if v == 0: return x,y
    return None

def _is_empty(board: List[List[int]], x:int, y:int) -> bool:
    return 0 <= y < len(board) and 0 <= x < len(board[0]) and board[y][x] == 0

def _to_int(v: Any) -> int:
    try: return int(float(v))
    except Exception: return -1

def _parse_xy(data: dict) -> Tuple[int,int]:
    if "x" in data and "y" in data:   return _to_int(data["x"]), _to_int(data["y"])
    if "col" in data and "row" in data: return _to_int(data["col"]), _to_int(data["row"])
    if "i" in data and "j" in data:   return _to_int(data["j"]), _to_int(data["i"])
    if "c" in data and "r" in data:   return _to_int(data["c"]), _to_int(data["r"])
    return -1, -1

def _format_history(history: Optional[List[HistoryMove]]) -> str:
    if not history: return "(none)"
    lines = []
    for idx, mv in enumerate(history, start=1):
        who = "Black(1)" if mv.player == 1 else "White(2)"
        lines.append(f"{idx}. {who}: (x={mv.x}, y={mv.y})")
    return "\n".join(lines)

def _print_virtual_board(board: List[List[int]], move: Tuple[int,int], player:int=2) -> None:
    x, y = move
    n = len(board)
    mp = {0:'.', 1:'●', 2:'○'}
    tmp = [row[:] for row in board]
    if 0 <= y < n and 0 <= x < n:
        tmp[y][x] = player
    header = "    " + " ".join(f"{i:2d}" for i in range(n))
    print("\n[VIRTUAL BOARD] top-left origin, x→, y↓")
    print(header)
    for r, row in enumerate(tmp):
        print(f"{r:2d}  " + " ".join(f"{mp[v]:2s}" for v in row))
    print(f"last move -> (x={x}, y={y}), player={player}\n")

def _call_openai_json(prompt: str, max_tokens: int):
    return client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system",
             "content": "You are a Gomoku AI. Output ONLY pure JSON that strictly conforms to the JSON Schema. No markdown, no comments, no extra keys."},
            {"role": "user", "content": prompt},
        ],
        temperature=0,
        max_tokens=max_tokens,
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "omok_move", "schema": RESPONSE_SCHEMA, "strict": True},
        },
    )

# ── 라우트 ─────────────────────────────────────────────────────────────
@app.get("/__ping__")
def ping():
    return {"ok": True, "model": OPENAI_MODEL, "board_size": BOARD_SIZE, "server": "llm_server"}

@app.post("/omok/move", response_model=OmokMoveRes)
def omok_move(req: OmokMoveReq) -> OmokMoveRes:
    size = len(req.board)

    # 보드↔로그 일치 검증
    if DEBUG:
        recon = _board_from_history(size, req.history)
        diffs = _diff_coords(recon, req.board)
        if diffs:
            print("[WARN] history ↔ board mismatch (count=%d)" % len(diffs))
            for x,y,a,b in diffs[:10]:
                print(f"  - at (x={x}, y={y}): from_history={a}, in_board={b}")
        else:
            print("[OK] history and board are consistent.")

    used = {(mv.x, mv.y) for mv in (req.history or [])}

    # 진행 로그: 최근 HISTORY_MAX 수만 사용
    hist_cut   = (req.history or [])[-HISTORY_MAX:]
    history_txt = _format_history(hist_cut)
    board_txt   = _format_board(req.board)

    prompt = f"""
You are a world-class Omok (Gomoku) AI, playing as white (2) on a {size}x{size} board.

Coordinate convention (IMPORTANT):
- Origin = top-left. 0-based indices.
- x = column (→ right), y = row (↓ down).
- Return ONLY JSON.

Rules:
- Never play on an occupied cell or outside the board.
- Always check in order: win(5) → block opponent's 5 → open-four/double-three/four-three.
- Prefer human-like choices when values are close (extend/attach within 1–2).
- Never miss a winning move.

Move log so far (do NOT repeat any of these coordinates):
{history_txt}

Board (0=empty, 1=black, 2=white):
{board_txt}

TASK:
1) Consider up to {N_CANDS} strong candidates.
2) For each candidate, compute a numeric score `llm_score` roughly on this scale:
   win=1e12, block_win=1e11, open4=2.5e9, semi4=1.2e9, open3=3.0e8,
   plus small bonuses for line extension and proximity.
3) Return JSON with your chosen move (x,y) and the candidates (ONLY x,y,llm_score — no other fields).
Make the candidate list spatially diverse: avoid near-duplicates (at most one move within a {CAND_MIN_DIST}×{CAND_MIN_DIST} neighborhood of a higher-scoring candidate).
""".strip()

    if DEBUG and PROMPT_LOG_MODE != "off":
        if PROMPT_LOG_MODE == "full":
            print("=== LLM PROMPT ==="); print(prompt); print("==================")
        else:
            print("=== LLM PROMPT (lite) ===")
            print(f"model={OPENAI_MODEL}, size={size}x{size}")
            print("Move log:"); print(history_txt or "(none)")
            print("[board omitted]"); print("=========================")

    # 호출 + 파싱 (재시도 포함)
    try:
        resp = _call_openai_json(prompt, MAX_TOKENS)
        text = (resp.choices[0].message.content or "").strip()
        if DEBUG:
            print("=== LLM RESPONSE ==="); print(text[:1000]); print("====================")
        data = _safe_json_loads(text)
    except json.JSONDecodeError:
        if DEBUG: print("[RETRY] parsing failed; retrying with larger max_tokens =", RETRY_MAX_TOKENS)
        resp = _call_openai_json(prompt, RETRY_MAX_TOKENS)
        text = (resp.choices[0].message.content or "").strip()
        if DEBUG:
            print("=== LLM RESPONSE (retry) ==="); print(text[:1400]); print("====================")
        data = _safe_json_loads(text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI 호출 실패: {e!r}")

    # 파싱
    x, y = _parse_xy(data)
    raw_cands = data.get("candidates")
    cand_models: Optional[List[Candidate]] = None
    if isinstance(raw_cands, list):
        cand_models = []
        for c in raw_cands:  # 전체 수집 후
            try:
                cx = _to_int(c.get("x", -1))
                cy = _to_int(c.get("y", -1))
                if not (0 <= cx < size and 0 <= cy < size):  # 보드 밖 제거
                    continue
                if not _is_empty(req.board, cx, cy):         # 점유칸 제거
                    continue
                cand_models.append(Candidate(
                    x=cx, y=cy, llm_score=float(c.get("llm_score", 0.0))
                ))
            except Exception:
                continue
        # 공간 다양화 + 최종 N개로 컷
        if cand_models:
            cand_models = _diversify_candidates(cand_models, N_CANDS, CAND_MIN_DIST)

    # 좌표 검증 & 후보 기반 보정
    def _valid(p: Tuple[int,int]) -> bool:
        xx, yy = p
        return (0 <= xx < size and 0 <= yy < size and
                _is_empty(req.board, xx, yy) and (xx,yy) not in used)

    if not _valid((x, y)) and cand_models:
        # cand_models는 이미 점수 내림차순으로 정렬된 상태는 아니므로 한 번 정렬
        cand_models.sort(key=lambda c: float(getattr(c, "llm_score", 0.0)), reverse=True)
        for c in cand_models:
            if _valid((c.x, c.y)):
                x, y = c.x, c.y
                if DEBUG: print(f"[FIX] picked from candidates -> (x={x}, y={y})")
                break

    # 그래도 안되면 스파이럴 폴백
    if not _valid((x, y)):
        cx = cy = size // 2
        spiral: List[Tuple[int,int]] = [(0,0)]
        for r in range(1, size):
            for dx in range(-r, r+1):
                spiral.append((dx, -r)); spiral.append((dx,  r))
            for dy in range(-r+1, r):
                spiral.append((-r, dy));  spiral.append(( r, dy))
        adjusted: Optional[Tuple[int,int]] = None
        for dx, dy in spiral:
            nx, ny = cx+dx, cy+dy
            if _valid((nx, ny)):
                adjusted = (nx, ny); break
        if adjusted is None:
            empty = _find_first_empty(req.board)
            if empty is None:
                raise HTTPException(status_code=502, detail="둘 수 있는 빈칸이 없습니다.")
            x, y = empty
        else:
            x, y = adjusted

    if DEBUG:
        _print_virtual_board(req.board, (x, y), player=2)

    res = OmokMoveRes(x=x, y=y, player=2)
    if cand_models:
        res.candidates = cand_models
    if DEBUG:
        res.debug_model = getattr(resp, "model", None) or OPENAI_MODEL
        res.server = "llm_server"
    return res

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("llm_server:app", host="127.0.0.1", port=8001, reload=True)
