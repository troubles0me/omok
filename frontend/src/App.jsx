// frontend/src/App.jsx
//App.jsx: onStartGame(settings)를 그대로 받아서 gameMode/aiDifficulty 외에 mode·gameId도 보존해 Game으로 전달.
import React, { useState } from "react";
import Lobby from "./components/Lobby";
import Game from "./components/Game";
import "./App.css";

function App() {
  const [gameSettings, setGameSettings] = useState(null);

  // settings 객체를 그대로 받되, 우리가 쓰는 키로 정규화 + 원본 보존
  const handleStartGame = (settings = {}) => {
    const gameMode = settings.gameMode ?? settings.mode ?? "pvai";
    const aiDifficulty = String(settings.aiDifficulty ?? settings.difficulty ?? "초급").trim();
    const mode = settings.mode ?? (gameMode === "pvp" ? (settings.mode || "create") : undefined);
    const joinId = settings.gameId || settings.id || undefined;

    setGameSettings({
      gameMode,
      aiDifficulty,
      mode,
      gameId: joinId,
      // 원본도 남겨둠(혹시 필요할 때)
      __raw: settings,
    });
  };

  const handleGoBackToLobby = () => setGameSettings(null);

  return (
    <div className="App">
      {!gameSettings ? (
        <Lobby onStartGame={handleStartGame} />
      ) : (
        <Game settings={gameSettings} onGoBack={handleGoBackToLobby} />
      )}
    </div>
  );
}

export default App;
