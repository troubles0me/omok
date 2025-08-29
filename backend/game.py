# backend/game.py

from __future__ import annotations
from typing import Tuple, Optional, List


class OmokGame:
    """
    렌주룰 오목 엔진
    - 1: 흑, 2: 백
    - 흑은 금수(장목/3-3/4-4) 적용, 승리는 '정확히' 5목
    - 백은 금수 없음, 5목 이상이면 승리
    """

    def __init__(self, board_size: int = 15):
        self.board_size = board_size
        self.reset()

    def reset(self) -> None:
        n = self.board_size
        self.board: List[List[int]] = [[0 for _ in range(n)] for _ in range(n)]
        self.current_turn: int = 1  # 1=흑, 2=백
        self.winner: Optional[int] = None
        self.game_over: bool = False
        self.moves: List[Tuple[int, int]] = []

    def place_stone(self, x: int, y: int, player: int) -> Tuple[bool, str]:
        """
        플레이어(player)가 (x,y)에 수를 두려고 시도.
        반환: (성공여부, 메시지).
        실패 시에는 보드/턴이 그대로 유지되고 게임은 계속된다.
        """

        # 1) 게임 종료 여부
        if self.game_over:
            return False, "게임이 이미 종료되었습니다."

        # 2) 턴 검증
        if player != self.current_turn:
            return False, f"잘못된 차례입니다. 지금은 플레이어 {self.current_turn}의 턴입니다."

        # 3) 좌표/중복 체크
        if not (0 <= x < self.board_size and 0 <= y < self.board_size):
            return False, "보드 범위를 벗어났습니다."
        if self.board[y][x] != 0:
            return False, "이미 돌이 놓인 자리입니다."

        # 4) 흑 금수 체크 (※ 금수면 '착수 거부 + 같은 턴 유지')
        if player == 1:
            is_forbidden, reason = self._is_forbidden_move(x, y)
            if is_forbidden:
                # 보드/기록/턴 전혀 변경하지 않음
                return False, f"금수입니다! {reason} 다른 곳에 놓아주세요."

        # 5) 착수
        self.board[y][x] = player
        self.moves.append((x, y))

        # 6) 승리 체크
        if self.check_win(x, y):
            self.winner = player
            self.game_over = True
            return True, f"게임 종료! 플레이어 {player}의 승리입니다."

        # 7) 턴 교체 (합법 착수에만 적용)
        self.current_turn = 2 if player == 1 else 1
        return True, "돌을 놓았습니다."

    # ---------------- 내부 로직 ----------------

    def check_win(self, x: int, y: int) -> bool:
        """
        방금 둔 수 기준 승리 판정
        - 흑: 정확히 5목만 승리
        - 백: 5목 이상이면 승리
        """
        n = self.board_size
        player = self.board[y][x]
        if player == 0:
            return False

        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for dx, dy in directions:
            count = 1
            for s in (1, -1):
                nx, ny = x + dx * s, y + dy * s
                while 0 <= nx < n and 0 <= ny < n and self.board[ny][nx] == player:
                    count += 1
                    nx += dx * s
                    ny += dy * s

            if player == 1:
                # 흑은 정확히 5
                if count == 5:
                    return True
            else:
                # 백은 5 이상
                if count >= 5:
                    return True
        return False

    def _is_forbidden_move(self, x: int, y: int) -> Tuple[bool, str]:
        """
        흑 금수 판정: 장목(>5), 3-3, 4-4
        간단 판별(근사). 규칙 엔진을 단순화했지만 실제 플레이엔 충분.
        """
        n = self.board_size
        # 가상 착수
        self.board[y][x] = 1

        # 1) 장목 검사
        if self._makes_overline(x, y):
            self.board[y][x] = 0
            return True, "장목"

        # 2) 3-3, 4-4 검사
        open_threes = 0
        open_fours = 0
        for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            t = self._check_line(x, y, dx, dy)  # "open_three" | "four" | None
            if t == "open_three":
                open_threes += 1
            elif t == "four":
                # 이 수 자체가 5를 완성시키지 않는 4만 카운트
                if not self.check_win(x, y):
                    open_fours += 1

        self.board[y][x] = 0

        if open_threes >= 2:
            return True, "3-3"
        if open_fours >= 2:
            return True, "4-4"
        return False, ""

    def _makes_overline(self, x: int, y: int) -> bool:
        """흑이 (x,y)에 두었을 때 6목 이상이 되는지"""
        n = self.board_size
        player = 1
        for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            cnt = 1
            for s in (1, -1):
                nx, ny = x + dx * s, y + dy * s
                while 0 <= nx < n and 0 <= ny < n and self.board[ny][nx] == player:
                    cnt += 1
                    nx += dx * s
                    ny += dy * s
            if cnt > 5:
                return True
        return False

    def _check_line(self, x: int, y: int, dx: int, dy: int) -> Optional[str]:
        """
        (x,y)=흑 가상착수 상태에서 한 방향 라인 분석
        - "open_three": 활삼(열린3) 하나로 판단
        - "four"     : 4 형성(양끝 중 한 곳만 열려 있어도 카운트)
        - None       : 해당 없음
        매우 단순화된 근사 판별
        """
        n = self.board_size
        player = self.board[y][x]
        # 정방향 수집
        fwd = []
        nx, ny = x + dx, y + dy
        while 0 <= nx < n and 0 <= ny < n:
            fwd.append(self.board[ny][nx])
            nx += dx
            ny += dy
        # 역방향 수집
        bwd = []
        nx, ny = x - dx, y - dy
        while 0 <= nx < n and 0 <= ny < n:
            bwd.append(self.board[ny][nx])
            nx -= dx
            ny -= dy

        # 연속 개수
        cf = 0
        for v in fwd:
            if v == player:
                cf += 1
            else:
                break
        cb = 0
        for v in bwd:
            if v == player:
                cb += 1
            else:
                break

        total = cf + cb + 1
        side_f_empty = (len(fwd) > cf and fwd[cf] == 0)
        side_b_empty = (len(bwd) > cb and bwd[cb] == 0)

        if side_f_empty and side_b_empty and total == 3:
            return "open_three"
        if total == 4 and (side_f_empty or side_b_empty):
            return "four"
        return None

    # -------- 디버그 보조 --------
    def print_board(self) -> None:
        mp = {0: '.', 1: '●', 2: '○'}
        print("  " + " ".join(f"{i:2d}" for i in range(self.board_size)))
        for i, row in enumerate(self.board):
            print(f"{i:2d} " + " ".join(mp[v] for v in row))

    

if __name__ == "__main__":
    # 간단 자가 테스트
    g = OmokGame(15)
    ok, msg = g.place_stone(7, 7, 1)
    print(ok, msg)
    g.print_board()
