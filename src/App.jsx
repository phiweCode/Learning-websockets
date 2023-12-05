import { PLAYER1, PLAYER2, createBoard, playMove } from "./game-logic/connect4";
import { useEffect, useState } from "react";
import "./App.css";

const websocket = new WebSocket("ws://localhost:8001/");

function initGame(websocket) {
  websocket.addEventListener("open", () => {
    // Send an "init" event according to who is connecting.
    const params = new URLSearchParams(window.location.search);
    let event = { type: "init" };
    if (params.has("join")) {
      // Second player joins an existing game.
      event.join = params.get("join");
    } else if (params.has("watch")) {
      // Spectator watches an existing game.
      event.watch = params.get("watch");
    } else {
      // First player starts a new game.
    }
    websocket.send(JSON.stringify(event));
  });
}

function showMessage(message) {
  window.setTimeout(() => window.alert(message), 50);
}

function receiveMoves(board, websocket) {
  websocket.addEventListener("message", ({ data }) => {
    const event = JSON.parse(data);
    switch (event.type) {
      case "play":
        // Update the UI with the move.
        playMove(board, event.player, event.column, event.row);
        break;
      case "win":
        showMessage(`Player ${event.player} wins!`);
        // No further messages are expected; close the WebSocket connection.
        websocket.close(1000);
        break;
      case "error":
        showMessage(event.message);
        break;
      case "init":
          // Create links for inviting the second player and spectators.
          document.querySelector(".join").href = "?join=" + event.join;
          document.querySelector(".watch").href = "?watch=" + event.watch;
          break;
      default:
        throw new Error(`Unsupported event type: ${event.type}.`);
    }
  });
}

function sendMoves(board, websocket) {
  // Don't send moves for a spectator watching a game.
  const params = new URLSearchParams(window.location.search);
  if (params.has("watch")) {
    return;
  }

  // When clicking a column, send a "play" event for a move in that column.
  board.addEventListener("click", ({ target }) => {
    const column = target.dataset.column;
    // Ignore clicks outside a column.
    if (column === undefined) {
      return;
    }
    const event = {
      type: "play",
      column: parseInt(column, 10),
    };
    websocket.send(JSON.stringify(event));
  });
}

function App() {
  useEffect(() => {
    const board = document.querySelector(".board");
    loadBoard(board);
    initGame(websocket);
    sendMoves(board, websocket);
    receiveMoves(board, websocket);
    window.addEventListener("DOMContentLoaded", loadBoard);

    return () => window.removeEventListener("DOMContentLoaded", loadBoard);
  }, []);

  const loadBoard = (board) => {
    createBoard(board);
  };

  return (
    <>
      <div class="actions">
        <a class="action new" href="/">
          New
        </a>
        <a class="action join" href="">
          Join
        </a>
        <a class="action watch" href="">
          Watch
        </a>
      </div>
      <div className="board"></div>
    </>
  );
}

export default App;
