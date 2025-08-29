// frontend/src/components/Lobby.jsx
//Lobby.jsx: AI(초급/고급) + PvP(방 만들기/참가) 둘 다 노출. onStartGame으로 설정 객체 전달.
import React, { useState } from "react";

function Lobby({ onStartGame }) {
  const [joinGameId, setJoinGameId] = useState("");

  return (
    <div className="lobby-container" style={{ textAlign: "center", marginTop: 40 }}>
      <h1>리액트 렌주룰 오목</h1>

      {/* AI 대전 */}
      <h2 style={{ marginTop: 20 }}>AI 대전 난이도 선택</h2>
      <div className="button-container" style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center", marginTop: 12 }}>
        <button onClick={() => onStartGame({ gameMode: "pvai", aiDifficulty: "초급" })}>
          AI 대전 (초급)
        </button>
        <button onClick={() => onStartGame({ gameMode: "pvai", aiDifficulty: "고급" })}>
          AI 대전 (고급)
        </button>
      </div>

      {/* PvP 대전 */}
      <h2 style={{ marginTop: 28 }}>PvP 대전</h2>
      <div className="button-container" style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center", marginTop: 12 }}>
        <button onClick={() => onStartGame({ gameMode: "pvp", mode: "create" })}>
          방 만들기
        </button>

        <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <input
            type="text"
            placeholder="게임 ID 입력"
            value={joinGameId}
            onChange={(e) => setJoinGameId(e.target.value)}
            style={{ padding: 8, width: 220 }}
          />
          <button
            onClick={() => {
              if (!joinGameId.trim()) return;
              onStartGame({ gameMode: "pvp", mode: "join", gameId: joinGameId.trim() });
            }}
          >
            방 참가
          </button>
        </div>
      </div>

      <style>{`
        .button-container button {
          padding: 12px 24px; font-size: 1.05rem; width: 300px; cursor: pointer; border: none;
          background-color: #4CAF50; color: white; border-radius: 6px; transition: background-color 0.2s;
        }
        .button-container button:hover { background-color: #45a049; }
      `}</style>
    </div>
  );
}

export default Lobby;
