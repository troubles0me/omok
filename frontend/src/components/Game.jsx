// frontend/src/components/Game.jsx
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import axios from "axios";
import Board from "./Board";

// ✅ 고정 엔드포인트
const API_URL = "http://4.217.179.111:8000/api";
const WS_URL  = "ws://4.217.179.111:8000/ws";

function Game({ settings, onGoBack }) {
  const gameMode = settings?.gameMode ?? "pvai";      // "pvai" | "pvp"
  const rawDiff  = settings?.aiDifficulty ?? settings?.difficulty ?? "초급";
  const difficulty = useMemo(() => String(rawDiff || "초급").trim(), [rawDiff]);
  const pvpMode  = settings?.mode;                    // "create" | "join"
  const joinId   = settings?.gameId;

  // ── 공통 상태 ──────────────────────────────────────────────────────────────
  const [gameId, setGameId] = useState(null);
  const [gameState, setGameState] = useState(null);
  const [message, setMessage] = useState("오목 게임을 시작합니다.");



  // 복사 함수
  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setMessage("방 코드가 복사되었습니다!");
      setTimeout(() => {
        setMessage("");
      }, 2000);
    } catch (err) {
      const textArea = document.createElement("textarea");
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand("copy");
        setMessage("방 코드가 복사되었습니다!");
      } catch (copyErr) {
        setMessage("복사 실패. 수동으로 복사해주세요.");
      }
      document.body.removeChild(textArea);
      setTimeout(() => {
        setMessage("");
      }, 2000);
    }
  };


  const [isBusy, setIsBusy]   = useState(false);

  // PvP 전용
  const [socket, setSocket] = useState(null);
  const [playerColor, setPlayerColor] = useState(null); // 1=흑, 2=백
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput]       = useState("");
  const bottomRef = useRef(null);

  // 고스트(미확정) 수
  const [pending, setPending] = useState(null);                                                                              // 최종수정:고스트돌 추가

  // AI 지원
  const [assistUsed, setAssistUsed] = useState(0);                                                                          // 최종수정: ai지원
  const ASSIST_LIMIT = 3;                                                                                                  // 최종수정: ai지원

  // 내 색/차례 헬퍼
  const myColor   = useMemo(() => (gameMode === "pvai" ? 1 : (playerColor ?? 1)), [gameMode, playerColor]);               // 최종수정:내 색 헬퍼 추가
  const isMyTurn  = useMemo(() => ((gameState?.current_turn ?? 1) === myColor), [gameState?.current_turn, myColor]);      // 최종수정:내 차례 헬퍼 추가

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMessages]);

  // ── 유틸 ───────────────────────────────────────────────────────────────────
  const normalizeServerMessage = useCallback((msg) => {
    if (!msg) return "";
    return msg.includes("금수") ? "금수입니다! 다른곳에 두세요" : msg;
  }, []);

  const normalizeDifficulty = useCallback((d) => {
    const r = String(d || "").trim().toLowerCase();
    if (["고급", "중급", "hard", "advanced", "pro"].includes(r)) return "고급";
    return "초급";
  }, []);

  const fetchGameState = useCallback(async (id) => {
    if (!id) return;
    const res = await axios.get(`${API_URL}/game/${id}`);
    setGameState(res.data);
    if (res?.data?.message) setMessage(normalizeServerMessage(res.data.message));
  }, [normalizeServerMessage]);

  // ── 초기화: PvAI / PvP(create/join) 분기 ──────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        setIsBusy(true);
        setMessage("게임 준비 중...");
        setPending(null);
        setAssistUsed(0); // 새 판마다 AI 지원 사용횟수 초기화                   최종수정:ai지원 추가

        if (gameMode === "pvai") {
          // PvAI: 새 게임 생성 → 상태 당겨오기
          const r = await axios.post(`${API_URL}/game/new`);
          const newid = r?.data?.id || r?.data?.game_id;                                                                    
          setGameId(newid);
          setPlayerColor(1);
          await fetchGameState(newid);
          setMessage("한 칸을 클릭해 위치를 선택한 뒤 '착수'를 누르세요.");       //최종수정:메시지 변경
          return;                                                           //최종수정: return;추가
        }

        // PvP
        if (pvpMode === "create") {                                         //최종수정:else if (gameMode === "pvp" && pvpMode === "create")에서 변경
          //  방 생성 직후 반드시 상태를 한 번 당겨와서 보드가 보이게 함
          const r = await axios.post(`${API_URL}/game/new`);
          const newid = r?.data?.id || r?.data?.game_id;
          setGameId(newid);
          setPlayerColor(Number(r?.data?.player_color) || 1);               //최종수정:setPlayerColor(1);에서 수정
          await fetchGameState(newid);
          setMessage("방이 생성되었습니다. 상대를 기다리세요.");                  //최종수정: 메시지 변경
          return;                                                           //최종수정: return;추가
        }

        if (pvpMode === "join" && joinId) {                                  //최종수정: else if (gameMode === "pvp" && pvpMode === "join" && joinId)에서 변경
          // 참가 직후에도 즉시 상태를 당겨옴
          setGameId(joinId);                              
          try {
            const j = await axios.post(`${API_URL}/game/${joinId}/join`);
            if (j?.data?.error) {
              setMessage(j.data.error);
            } else {
              setPlayerColor(Number(j?.data?.player_color) || 2);
              await fetchGameState(joinId);
              setMessage("게임에 참가했습니다.");
            }
          } catch {
            setMessage("게임 참가 실패");
          }
        }
      } catch (e) {
        console.error(e);
        setMessage("게임 생성/참가 실패");
      } finally {
        setIsBusy(false);
      }
    })();
  }, [gameMode, pvpMode, joinId, fetchGameState]);

  // PvP WebSocket 연결
  useEffect(() => {
    if (gameMode !== "pvp" || !gameId) return;

    const ws = new WebSocket(`${WS_URL}/${gameId}`);
    setSocket(ws);

    ws.onopen = () => {
      console.log("WebSocket 연결됨");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket 메시지:", data);

        if (data.type === "game_update") {
          setGameState(data.payload);
          if (data.payload.message) {
            setMessage(normalizeServerMessage(data.payload.message));
          }
        } else if (data.type === "chat_message") {
          setChatMessages(prev => [...prev, data.payload]);
        } else if (data.type === "system") {
          setMessage(data.payload.message);
        }
      } catch (e) {
        console.error("WebSocket 메시지 파싱 오류:", e);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket 연결 종료");
      setSocket(null);
    };

    return () => {
      ws.close();
    };
  }, [gameMode, gameId, normalizeServerMessage]);

  // ── 착수 ───────────────────────────────────────────────────────────────────
  const placeStone = useCallback(async (x, y) => {
    if (!gameId || isBusy || !isMyTurn) return; // 내 차례가 아니면 무시

    try {
      setIsBusy(true);
      setPending({ x, y }); // 고스트 돌 표시

      const res = await axios.post(`${API_URL}/game/${gameId}/move`, {
        x, y, player: myColor
      });

      setPending(null); // 고스트 돌 제거
      setGameState(res.data);
      
      if (res.data.message) {
        setMessage(normalizeServerMessage(res.data.message));
      }

      // 승리 체크
      if (res.data.winner) {
        const winnerText = res.data.winner === myColor ? "승리!" : "패배...";
        setMessage(winnerText);
        return;
      }

      // PvAI에서 AI 차례
      if (gameMode === "pvai" && res.data.current_turn === 2) {
        setMessage("AI가 생각 중...");
        try {
          const aiRes = await axios.post(`${API_URL}/game/${gameId}/ai-move`, {
            difficulty: difficulty
          });
          setGameState(aiRes.data);
          
          if (aiRes.data.winner) {
            const aiWinnerText = aiRes.data.winner === myColor ? "승리!" : "패배...";
            setMessage(aiWinnerText);
          } else {
            setMessage("AI가 착수했습니다. 당신 차례입니다.");
          }
        } catch (aiError) {
          console.error("AI 착수 오류:", aiError);
          setMessage("AI 착수 실패");
        }
      }
    } catch (e) {
      console.error("착수 오류:", e);
      setPending(null);
      if (e.response?.data?.detail) {
        setMessage(e.response.data.detail);
      } else {
        setMessage("착수 실패");
      }
    } finally {
      setIsBusy(false);
    }
  }, [gameId, isBusy, isMyTurn, myColor, gameMode, difficulty, normalizeServerMessage]);

  // ── AI 지원 ────────────────────────────────────────────────────────────────
  const requestAssist = useCallback(async () => {
    if (!gameId || isBusy || !isMyTurn || assistUsed >= ASSIST_LIMIT) return;

    try {
      setIsBusy(true);
      setMessage("AI가 추천 좌표를 계산 중...");

      const res = await axios.post(`${API_URL}/game/${gameId}/assist`, {
        player: myColor,
        difficulty: difficulty
      });

      setAssistUsed(prev => prev + 1);
      setMessage(`AI 추천: (${res.data.x}, ${res.data.y}) - ${res.data.message} (${ASSIST_LIMIT - assistUsed - 1}회 남음)`);
      
      // 추천 좌표를 pending으로 표시
      setPending({ x: res.data.x, y: res.data.y });
      
      // 3초 후 pending 제거
      setTimeout(() => setPending(null), 3000);
      
    } catch (e) {
      console.error("AI 지원 오류:", e);
      if (e.response?.data?.detail) {
        setMessage(e.response.data.detail);
      } else {
        setMessage("AI 지원 실패");
      }
    } finally {
      setIsBusy(false);
    }
  }, [gameId, isBusy, isMyTurn, assistUsed, ASSIST_LIMIT, myColor, difficulty]);

  // ── 채팅 ───────────────────────────────────────────────────────────────────
  const sendChat = useCallback(() => {
    if (!chatInput.trim() || !socket) return;
    
    socket.send(JSON.stringify({
      type: "chat_message",
      payload: { message: chatInput.trim() }
    }));
    
    setChatInput("");
  }, [chatInput, socket]);

  // ── 렌더링 ─────────────────────────────────────────────────────────────────
  if (!gameState) {
    return (
      <div className="game-container">
        <div className="game-header">
          <button onClick={onGoBack} className="back-button">← 뒤로</button>
          <h2>게임 준비 중...</h2>
        </div>
        <div className="game-content">
          <p>{message}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="game-container">
      <div className="game-header">
        <button onClick={onGoBack} className="back-button">← 뒤로</button>
        <h2>오목 게임</h2>
        <div className="game-info">
          <span>모드: {gameMode === "pvai" ? "AI 대전" : "PvP"}</span>
          {gameMode === "pvai" && <span>난이도: {difficulty}</span>}
          {gameMode === "pvp" && <span>색: {playerColor === 1 ? "흑" : "백"}</span>}
        </div>
      </div>

      <div className="game-content">
        <div className="game-board">
          <Board 
            board={gameState.board} 
            onCellClick={placeStone}
            pending={pending}
            disabled={!isMyTurn || isBusy}
          />
          
          {gameMode === "pvai" && isMyTurn && !gameState.winner && (
            <div className="ai-assist">
              <button 
                onClick={requestAssist}
                disabled={assistUsed >= ASSIST_LIMIT || isBusy}
                className="assist-button"
              >
                AI 지원 ({ASSIST_LIMIT - assistUsed}회 남음)
              </button>
            </div>
          )}
        </div>

        <div className="game-sidebar">
          <div className="game-status">
            <h3>게임 상태</h3>
            <p>현재 턴: {gameState.current_turn === 1 ? "흑" : "백"}</p>
            {gameState.winner && (
              <p className="winner">
                승자: {gameState.winner === 1 ? "흑" : "백"}
              </p>
            )}
            <p className="message">{message}</p>
            
            {/* PvP 모드에서 방 코드 표시 */}
            {gameMode === "pvp" && gameId && (
              <div className="room-info">
                <h4>방 정보</h4>
                <p><strong>내 색:</strong> {playerColor === 1 ? "흑" : "백"}</p>
                {pvpMode === "create" && (
                  <div className="join-instructions">
                    <p>상대방에게 이 방 코드를 알려주세요:</p>
                    <div className="room-code-display">
                      <input 
                        type="text" 
                        value={gameId} 
                        readOnly 
                        className="room-code-input"
                      />
                      <button 
                        onClick={() => copyToClipboard(gameId)}
                        className="copy-button"
                      >
                        복사
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {gameMode === "pvp" && (
            <div className="chat-section">
              <h3>채팅</h3>
              <div className="chat-messages">
                {chatMessages.map((msg, idx) => (
                  <div key={idx} className="chat-message">
                    <span className="sender">{msg.sender}:</span>
                    <span className="message">{msg.message}</span>
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
              <div className="chat-input">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && sendChat()}
                  placeholder="메시지를 입력하세요..."
                  disabled={!socket}
                />
                <button onClick={sendChat} disabled={!chatInput.trim() || !socket}>
                  전송
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Game;
