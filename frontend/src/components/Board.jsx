import React, { useMemo } from "react";
import "./Board.css";

function Board({ board = [], onCellClick, pending = null, disabled = false }) {
  const n = board.length || 15;

  const hoshi = useMemo(() => {
    if (n === 15) return [[3,3],[3,11],[11,3],[11,11],[7,7]];
    if (n === 19) return [[3,3],[3,9],[3,15],[9,3],[9,9],[9,15],[15,3],[15,9],[15,15]];
    const c = Math.floor(n/2);
    return [[c,c]];
  }, [n]);

  const handleCellClick = (x, y) => {
    if (!disabled && onCellClick) {
      onCellClick(x, y);
    }
  };

  const handleKeyDown = (e, x, y) => {
    if (!disabled && (e.key === "Enter" || e.key === " ")) {
      handleCellClick(x, y);
    }
  };

  return (
    <div className="board-wrap">
      <div className="board" style={{ "--n": n }}>
        {board.map((row, y) =>
          row.map((cell, x) => {
            const isPending = pending && pending.x === x && pending.y === y && cell === 0;

            return (
              <div
                key={`${x}-${y}`}
                className={`cell ${disabled ? 'disabled' : ''}`}
                style={{ gridColumnStart: x + 1, gridRowStart: y + 1 }}
                onClick={() => handleCellClick(x, y)}
                data-x={x}
                data-y={y}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => handleKeyDown(e, x, y)}
              >
                {cell === 1 ? <div className="stone black" aria-hidden="true" /> : null}
                {cell === 2 ? <div className="stone white" aria-hidden="true" /> : null}

                {isPending ? (
                  <div
                    className="stone black ghost"
                    aria-hidden="true"
                  />
                ) : null}
              </div>
            );
          })
        )}

        {hoshi.map(([x, y]) => (
          <div
            key={`h-${x}-${y}`}
            className="hoshi"
            style={{
              gridColumnStart: x + 1,
              gridRowStart: y + 1,
              pointerEvents: "none",
              zIndex: 0
            }}
            aria-hidden="true"
          />
        ))}
      </div>
    </div>
  );
}

export default React.memo(Board);
