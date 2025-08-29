# -*- coding: utf-8 -*-
# backend/ai.py
import json
import random
import requests
from typing import List, Dict, Tuple, Optional
from math import exp
import os
import time
print("OMOK_LLM_URL =", os.getenv("OMOK_LLM_URL"))

class LLMError(RuntimeError):
    pass

def _maybe_sleep_delay():
    """강제 수 선택 후 휴리스틱이 너무 즉답하지 않도록 1초 정도 지연"""
    try:
        delay = float(os.getenv("OMOK_FORCE_DELAY_SEC", "1.0"))  # 기본 1초, .env로 조정 가능
    except Exception:
        delay = 1.0
    if delay > 0:
        time.sleep(delay)

def _get_llm_url() -> str:
    return os.getenv("OMOK_LLM_URL") or ""

def _get_timeout() -> float:
    try:
        return float(os.getenv("OMOK_LLM_TIMEOUT_SEC", "20"))
    except Exception:
        return 20.0

# ====== 튜닝 가능한 가중치 (원하면 .env 로 조절) ======
CENTER_SCALE       = float(os.getenv("OMOK_CENTER_SCALE", "200000"))     # 중앙 보너스 최대치(초반)
NEIGHBOR_BONUS     = float(os.getenv("OMOK_NEIGHBOR_BONUS", "300000"))   # 인접 보너스
EXPLORATION_K      = int  (os.getenv("OMOK_EXPLORATION_K", "30"))        # 탐색 후보 추가 수
JITTER_RANGE       = float(os.getenv("OMOK_JITTER_RANGE", "5000"))       # 동점 무작위 ±값
NEAR_RADIUS        = int  (os.getenv("OMOK_NEAR_RADIUS", "2"))           # 근접 반경

# 방어 가중치(상대 위협 차단을 크게 → 강제 수 아닌 구간에서 휴리스틱이 알아서 막음)
BLOCK_OPEN4_BONUS  = float(os.getenv("OMOK_BLOCK_OPEN4_BONUS",  "7000000000"))  # 7e9
BLOCK_SEMI4_BONUS  = float(os.getenv("OMOK_BLOCK_SEMI4_BONUS",  "6000000000"))  # 6e9
BLOCK_OPEN3_BONUS  = float(os.getenv("OMOK_BLOCK_OPEN3_BONUS",  "5000000000"))  # 5e9

# 강제수 모드: strict(기본)=즉승/즉패만, plus4=+상대4 차단, all=+열린3까지
FORCE_MODE = os.getenv("OMOK_FORCE_MODE", "all").lower()
AI_DEBUG   = os.getenv("OMOK_AI_DEBUG", "0") == "1"

DIRS: Tuple[Tuple[int,int], ...] = ((1,0),(0,1),(1,1),(1,-1))
DIFF_PROFILES = {
    "초급": {
        "force_block_open3_prob": float(os.getenv("OMOK_BEGINNER_BLOCK_OPEN3_PROB", "0.35")),  # 35% 확률로만 열린3 차단
        "topk": int(os.getenv("OMOK_BEGINNER_TOPK", "4")),          # 상위 K 후보 중에서
        "temperature": float(os.getenv("OMOK_BEGINNER_TEMP", "0.85")), # 온도 샘플링
        "alpha_blend": float(os.getenv("OMOK_BEGINNER_ALPHA", "0.7")),  # LLM 비중 ↑
        "jitter": float(os.getenv("OMOK_BEGINNER_JITTER", "12000")),    # 가벼운 흔들림↑
        "exploration_k": int(os.getenv("OMOK_BEGINNER_EXPLORATION_K", "45")),
        "center_scale": float(os.getenv("OMOK_BEGINNER_CENTER_SCALE", "260000")),
        "near_radius": int(os.getenv("OMOK_BEGINNER_NEAR_RADIUS", "2")),
        # 반드시 강제: 내 5, 상대 5, 상대 열린4/민4. (열린3은 확률적)
        "force_block_open4": True,
        "force_block_semi4": True,
    },
    "고급": {
        "force_block_open3_prob": 1.0,            # 사실상 항상 차단
        "topk": 1,                                 # 최적 한 점
        "temperature": 0.0,                        # 샘플링 없이 결정적
        "alpha_blend": float(os.getenv("OMOK_ADV_ALPHA", "0.35")),    # LLM 비중 낮게
        "jitter": float(os.getenv("OMOK_ADV_JITTER", "1500")),
        "exploration_k": int(os.getenv("OMOK_ADV_EXPLORATION_K", "25")),
        "center_scale": float(os.getenv("OMOK_ADV_CENTER_SCALE", "180000")),
        "near_radius": int(os.getenv("OMOK_ADV_NEAR_RADIUS", "2")),
        "force_block_open4": True,
        "force_block_semi4": True,
    },
}

def _get_profile(difficulty: str) -> dict:
    return DIFF_PROFILES.get(difficulty or "초급", DIFF_PROFILES["초급"])

def _in_bounds(board, y, x):
    return 0 <= y < len(board) and 0 <= x < len(board[0])

def _count_line(board, y, x, dy, dx, who):
    cnt = 0
    ny, nx = y + dy, x + dx
    while _in_bounds(board, ny, nx) and board[ny][nx] == who:
        cnt += 1
        ny += dy; nx += dx
    return cnt

def _find_must_block_move_for_beginner(board: List[List[int]], me: int, p_open3: float,
                                       force_open4: bool, force_semi4: bool):
    """승/패, 열린4/민4는 항상 막고, 열린3은 확률 p로만 막기. 막을 좌표 하나 반환 or None"""
    import random
    opp = 1 if me == 2 else 2

    # ① 내 즉승
    n = len(board)
    for y in range(n):
        for x in range(n):
            if board[y][x] == 0 and _makes_n(board, x, y, me, 5):
                return (x, y)

    # ② 상대 즉승 차단
    for y in range(n):
        for x in range(n):
            if board[y][x] == 0 and _makes_n(board, x, y, opp, 5):
                return (x, y)

    # ③ 상대 열린4/민4 차단 (항상)
    if force_open4 or force_semi4:
        for y in range(n):
            for x in range(n):
                if board[y][x] != 0: continue
                pf = _pattern_flags(board, x, y, opp)
                if force_open4 and pf["open4"]:
                    return (x, y)
                if force_semi4 and pf["semi4"]:
                    return (x, y)

    # ④ 상대 열린3 차단 (확률)
    if p_open3 > 0.0 and random.random() < p_open3:
        best = None
        for y in range(n):
            for x in range(n):
                if board[y][x] != 0: continue
                pf = _pattern_flags(board, x, y, opp)
                if pf["open3"]:
                    # 열린3이 여러 곳이면 아무거나(첫번째) 선택
                    best = (x, y); break
            if best: break
        if best: return best

    return None

def _line_info(board, y, x, dy, dx, who):
    c1 = _count_line(board, y, x,  dy, dx,  who)
    c2 = _count_line(board, y, x, -dy,-dx, who)
    length = 1 + c1 + c2
    ny1, nx1 = y + dy*(c1+1), x + dx*(c1+1)
    ny2, nx2 = y - dy*(c2+1), x - dx*(c2+1)
    open1 = _in_bounds(board, ny1, nx1) and board[ny1][nx1] == 0
    open2 = _in_bounds(board, ny2, nx2) and board[ny2][nx2] == 0
    opens = (1 if open1 else 0) + (1 if open2 else 0)
    return length, opens

def _makes_n(board, x, y, who, n):
    if board[y][x] != 0: return False
    board[y][x] = who
    ok = False
    for dy,dx in DIRS:
        l, _ = _line_info(board, y, x, dy, dx, who)
        if l >= n:
            ok = True; break
    board[y][x] = 0
    return ok

def _pattern_flags(board, x, y, who):
    if board[y][x] != 0:
        return {"open4": False, "semi4": False, "open3": False}
    board[y][x] = who
    open4 = semi4 = open3 = False
    for dy,dx in DIRS:
        l, op = _line_info(board, y, x, dy, dx, who)
        if l == 4 and op == 2: open4 = True
        if l == 4 and op >= 1: semi4 = True
        if l == 3 and op == 2: open3 = True
    board[y][x] = 0
    return {"open4": open4, "semi4": semi4, "open3": open3}

def _has_neighbor(board, x, y, r=NEAR_RADIUS):
    n = len(board)
    for dy in range(-r, r+1):
        for dx in range(-r, r+1):
            if dx==0 and dy==0: continue
            yy, xx = y+dy, x+dx
            if 0<=yy<n and 0<=xx<n and board[yy][xx]!=0:
                return True
    return False

def _stones_count(board: List[List[int]]) -> int:
    return sum(1 for row in board for v in row if v != 0)

def _phase_center_factor(board: List[List[int]]) -> float:
    s = _stones_count(board)
    return max(0.0, 1.0 - (s / 40.0))  # 0..1

def _center_bonus(board, x, y) -> float:
    n = len(board)
    cx = cy = (n-1)/2.0
    dist2 = (x-cx)**2 + (y-cy)**2
    maxd = ((n-1)/2.0)**2 * 2
    return 1.0 - (dist2 / maxd)

def _score_move(board: List[List[int]], x: int, y: int, me: int,
                center_scale: float, center_phase: float) -> float:
    if board[y][x] != 0: return -1e15
    opp = 1 if me == 2 else 2

    # 1) 즉승 / 즉패 차단
    if _makes_n(board, x, y, me, 5):  return 1e12
    if _makes_n(board, x, y, opp, 5): return 1e11

    # 2) 패턴 (내 강점 + 상대 위협 차단 가중)
    myp  = _pattern_flags(board, x, y, me)
    oppp = _pattern_flags(board, x, y, opp)
    score = 0.0
    if myp["open4"]:  score += 2.5e9
    if myp["semi4"]:  score += 1.2e9
    if myp["open3"]:  score += 3.0e8
    if oppp["open4"]: score += BLOCK_OPEN4_BONUS
    if oppp["semi4"]: score += BLOCK_SEMI4_BONUS
    if oppp["open3"]: score += BLOCK_OPEN3_BONUS

    # 3) 연장 선호
    for dy,dx in DIRS:
        l, op = _line_info(board, y, x, dy, dx, me)
        score += l * 1e6 + op * 2e5

    # 4) 근접/중앙
    if _has_neighbor(board, x, y, r=NEAR_RADIUS):
        score += NEIGHBOR_BONUS
    score += _center_bonus(board, x, y) * center_scale * center_phase

    # 5) 동점 무작위성
    if JITTER_RANGE > 0:
        score += random.uniform(-JITTER_RANGE, JITTER_RANGE)

    return score

def _sample_from_topk(scored: List[Tuple[Tuple[int,int], float]], k: int, T: float) -> Tuple[int,int]:
    """[(pos, score)]를 점수 내림차순 정렬된 상태로 받고, Top-K에서 softmax(T)로 샘플"""
    if not scored:
        return (0, 0)
    scored = sorted(scored, key=lambda t: t[1], reverse=True)
    top = scored[:max(1, k)]
    if T <= 1e-9 or len(top) == 1:
        return top[0][0]
    # 안정적 softmax
    m = max(s for _, s in top)
    ws = [exp((s - m) / max(1e-9, T)) for _, s in top]
    S = sum(ws)
    import random
    r = random.random() * S
    acc = 0.0
    for (pos, s), w in zip(top, ws):
        acc += w
        if r <= acc:
            return pos
    return top[-1][0]

def _best_by_heuristic_with_profile(board: List[List[int]], me: int, profile: dict) -> Dict[str,int]:
    # 프로파일에서 동적 파라미터 반영
    global EXPLORATION_K, JITTER_RANGE, CENTER_SCALE, NEAR_RADIUS
    EXPLORATION_K_OLD, JITTER_OLD, CENTER_OLD, NEAR_OLD = EXPLORATION_K, JITTER_RANGE, CENTER_SCALE, NEAR_RADIUS
    EXPLORATION_K = profile["exploration_k"]
    JITTER_RANGE  = profile["jitter"]
    CENTER_SCALE  = profile["center_scale"]
    NEAR_RADIUS   = profile["near_radius"]

    try:
        n = len(board)
        center_phase = _phase_center_factor(board)
        center_scale = CENTER_SCALE

        # 후보 생성
        candidates = _collect_candidates(board)
        if not candidates:
            candidates = [(x,y) for y in range(n) for x in range(n) if board[y][x]==0]

        # 점수 매기기
        scored = []
        for x,y in candidates:
            s = _score_move(board, x, y, me, center_scale, center_phase)
            scored.append(((x,y), s))

        # 선택: 고급은 best 1점, 초급은 Top-K 샘플링
        if profile["topk"] <= 1:
            best_pos = max(scored, key=lambda t: t[1])[0]
        else:
            best_pos = _sample_from_topk(scored, k=profile["topk"], T=profile["temperature"])
        return {"x": best_pos[0], "y": best_pos[1]}
    finally:
        # 전역 복구
        EXPLORATION_K, JITTER_RANGE, CENTER_SCALE, NEAR_RADIUS = EXPLORATION_K_OLD, JITTER_OLD, CENTER_OLD, NEAR_OLD


def _collect_candidates(board: List[List[int]]) -> List[Tuple[int,int]]:
    n = len(board)
    near = [(x,y) for y in range(n) for x in range(n)
            if board[y][x]==0 and _has_neighbor(board,x,y,NEAR_RADIUS)]
    if near and len(near) >= 20:
        return near
    empties = [(x,y) for y in range(n) for x in range(n) if board[y][x]==0]
    def center_key(p): return _center_bonus(board, p[0], p[1])
    extras = sorted(empties, key=center_key, reverse=True)[:EXPLORATION_K]
    seen = set(near)
    return near + [p for p in extras if p not in seen]

# ============ 강제 수(무조건 막기/두기) ============

def _forced_move(board: List[List[int]], me: int = 2) -> Optional[Dict[str,int]]:
    """
    FORCE_MODE:
      - strict (default): 내 즉승, 상대 즉승차단만
      - plus4:           + 상대 '바로 4'를 만드는 수 차단(엔드포인트 봉쇄)
      - all:             + 상대가 두면 열린3/민4 되는 자리까지 차단
    """
    opp = 1 if me == 2 else 2
    n = len(board)

    my_wins, opp_win_blocks = [], []
    opp_four_blocks, opp_open3_blocks = [], []

    for y in range(n):
        for x in range(n):
            if board[y][x] != 0:
                continue

            # 1) 내 즉승
            if _makes_n(board, x, y, me, 5):
                my_wins.append((x, y))
                continue

            # 2) 상대 즉승 차단
            if _makes_n(board, x, y, opp, 5):
                opp_win_blocks.append((x, y))
                continue

            if FORCE_MODE in ("plus4", "all"):
                # 상대가 두면 4가 되는지(엔드포인트 차단 목적)
                board[y][x] = opp
                o_open4 = o_semi4 = o_open3 = False
                for dy, dx in DIRS:
                    l, op = _line_info(board, y, x, dy, dx, opp)
                    if l == 4 and op == 2: o_open4 = True
                    if l == 4 and op >= 1: o_semi4 = True
                    if l == 3 and op == 2: o_open3 = True
                board[y][x] = 0

                if o_open4 or o_semi4:
                    opp_four_blocks.append((x, y))
                elif FORCE_MODE == "all" and o_open3:
                    opp_open3_blocks.append((x, y))

    def _pick_best(moves: List[Tuple[int,int]]) -> Optional[Dict[str,int]]:
        if not moves:
            return None
        center_phase = _phase_center_factor(board)
        best = None
        best_s = -1e18
        for x, y in moves:
            s = _score_move(board, x, y, me, CENTER_SCALE, center_phase)
            if s > best_s:
                best_s = s
                best = {"x": x, "y": y}
        return best

    for bucket, tag in (
        (my_wins, "my_win"),
        (opp_win_blocks, "opp_win_block"),
        (opp_four_blocks if FORCE_MODE in ("plus4","all") else [], "opp_four_block"),
        (opp_open3_blocks if FORCE_MODE == "all" else [], "opp_open3_block"),
    ):
        pick = _pick_best(bucket)
        if pick is not None:
            if AI_DEBUG:
                print(f"[FORCED] {tag} -> {pick}")
            return pick

    return None

# ============ 일반 휴리스틱 / LLM 블렌딩 ============

def _best_by_heuristic(board: List[List[int]], me: int = 2) -> Dict[str, int]:
    n = len(board)
    center_phase = _phase_center_factor(board)
    center_scale = CENTER_SCALE

    candidates = _collect_candidates(board)
    if not candidates:
        candidates = [(x,y) for y in range(n) for x in range(n) if board[y][x]==0]

    best = {"x": 0, "y": 0}
    best_s = -1e18
    for x,y in candidates:
        s = _score_move(board, x, y, me, center_scale, center_phase)
        if s > best_s:
            best_s = s; best = {"x": x, "y": y}
    return best

def _ask_llm(board: List[List[int]], difficulty: str, history=None) -> Dict[str, int]:
    prof = _get_profile(difficulty)
    llm_url = _get_llm_url()
    if not llm_url:
        raise LLMError("OMOK_LLM_URL이 설정되어 있지 않습니다.")

    n_samples = max(1, int(os.getenv("OMOK_LLM_N_SAMPLES", "1")))
    alpha = prof["alpha_blend"]  # ⬅ 난이도별 alpha
    center_phase = _phase_center_factor(board)

    best = None
    best_s = -1e18

    for _ in range(n_samples):
        payload = {"board": board, "difficulty": difficulty or "초급", "player": 2}
        if history:
            payload["history"] = history
        try:
            resp = requests.post(llm_url, json=payload, timeout=_get_timeout())
        except requests.RequestException as e:
            raise LLMError(f"LLM 서버 연결 실패: {e!r}")
        if resp.status_code != 200:
            raise LLMError(f"LLM 서버 오류: {resp.status_code} {resp.text}")

        data = resp.json()
        raw_cands = data.get("candidates")

        def _srv_score(x, y):
            return _score_move(board, x, y, me=2,
                               center_scale=CENTER_SCALE,
                               center_phase=center_phase)

        scored = []
        if isinstance(raw_cands, list) and raw_cands:
            for c in raw_cands:
                try:
                    x, y = int(c["x"]), int(c["y"])
                    if not (0 <= y < len(board) and 0 <= x < len(board[0])): 
                        continue
                    if board[y][x] != 0: 
                        continue
                    llm_s = float(c.get("llm_score", 0.0))
                    srv_s = _srv_score(x, y)
                    s = alpha * llm_s + (1.0 - alpha) * srv_s
                    scored.append(((x,y), s))
                except Exception:
                    continue
            if scored:
                # 초급: Top-K 샘플링, 고급: 최고점
                if prof["topk"] > 1:
                    pos = _sample_from_topk(scored, k=prof["topk"], T=prof["temperature"])
                else:
                    pos = max(scored, key=lambda t: t[1])[0]
                s = next(s for p,s in scored if p == pos)
                if s > best_s: best_s, best = s, {"x": pos[0], "y": pos[1]}
        if best is None and "x" in data and "y" in data:
            try:
                x, y = int(data["x"]), int(data["y"])
                if 0 <= y < len(board) and 0 <= x < len(board[0]) and board[y][x] == 0:
                    s = _srv_score(x, y)
                    if s > best_s:
                        best_s, best = s, {"x": x, "y": y}
            except Exception:
                pass

    if best is None:
        best = _best_by_heuristic_with_profile(board, me=2, profile=prof)
    return best

def _rule_based_ai(board: List[List[int]]) -> Dict[str, int]:
    return _best_by_heuristic(board, me=2)

def find_best_move(board: List[List[int]], difficulty: str, history=None) -> Dict[str, int]:
    prof = _get_profile(difficulty)

    # 0) 초·고급 모두 공통: 즉승/상대 5/열린4/민4는 “항상” 강제
    #    열린3은 난이도에 따라 확률적으로만 강제
    forced = _find_must_block_move_for_beginner(
        board, me=2,
        p_open3=prof["force_block_open3_prob"],
        force_open4=prof["force_block_open4"],
        force_semi4=prof["force_block_semi4"],
    )
    if forced is not None:
        _maybe_sleep_delay()
        return {"x": forced[0], "y": forced[1]}

    # 1) 난이도 분기: 고급 = 순수 휴리스틱(결정적), 초급 = LLM 블렌딩 + 샘플링
    if difficulty == "고급":
        move = _best_by_heuristic_with_profile(board, me=2, profile=prof)
        _maybe_sleep_delay()   # ⬅️ 고급 난이도도 동일하게 지연
        return move
    else:
        return _ask_llm(board, difficulty or "초급", history=history)
