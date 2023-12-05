import asyncio
import itertools
import json

import websockets

from connect4 import PLAYER1, PLAYER2, Connect4

import secrets


JOIN = {}

WATCH = {}

async def error(websocket, message):

    """
    Sends an  error message

    """

    event = {
        "type": "error",
        "message": message,
    }
    await websocket.send(json.dumps(event))


async def replay(websocket, game):
    """
    Sends the previous move.

    """

    # Make a copy to avoid an exception if game.move changes while iteration
    # is in progress. If a move is played while replay is running, move will
    # be sent out of order but each move will be sent once and eventually the
    # UI will be consistent.

    for player, column, row in game.moves.copy():
        event = {
            "type": player,
            "column": column,
            "row": row,
        }
        await websocket.send(json.dumps(event))

async def play(websocket, game, player, connected):
    """
    Recieve and process moves from a player


    """

    async for message in websocket:
       # Parse a "play" event from the UI.
       event = json.loads(message)
       assert event["type"] == "play"
       column = event["column"]

       try:
           # Play the move.
           row = game.play(player, column)
       except RuntimeError as exc:
           # Send an "error" event if the move was illegal.
           await error(websocket, str(exc))
           continue

       # Send a "play" event to update the UI.
       event = {
         "type": "play",
         "player": player,
         "column": column,
         "row": row,
       }
       websockets.broadcast(connected,json.dumps(event))

       # if move is winning, send a "win" event.
       if game.winner is not None:

           event = {
                "type": "win",
                "player": game.winner,
            }

           websockets.broadcast(connected, json.dumps(event))


async def start(websocket):
    # Initialize a Connect Four game, the set of WebSocket connections
    # receiving moves from this game, and secret access token.
    game = Connect4()
    connected = {websocket}

    join_key = secrets.token_urlsafe(12)
    JOIN[join_key] = game, connected

    try:
        # Send the secret access token to the browser of the first player,
        # where it'll be used for building a "join" link.
        event = {
            "type": "init",
            "join": join_key,
        }
        await websocket.send(json.dumps(event))

        # Temporary - for testing.
        print("first player started game", id(game))
        async for message in websocket:
            print("first player sent", message)

    finally:
        del JOIN[join_key]


async def join(websocket, join_key):
    # Find the Connect Four game.
    try:
        game, connected = JOIN[join_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    # Register to receive moves from this game.
    connected.add(websocket)
    try:

        # Temporary - for testing.
        print("second player joined game", id(game))
        async for message in websocket:
            print("second player sent", message)

    finally:
        connected.remove(websocket)

async def watch(websocket, watch_key):
    """
    Handle a connection from a spectator: watch an existing game.

    """
    # Find the Connect Four game.
    try:
        game, connected = WATCH[watch_key]
    except KeyError:
        await error(websocket, "Game not found.")
        return

    # Register to receive moves from this game.
    connected.add(websocket)
    try:
        # Send previous moves, in case the game already started.
        await replay(websocket, game)
        # Keep the connection open, but don't receive any messages.
        await websocket.wait_closed()
    finally:
        connected.remove(websocket)

async def handler(websocket):
    # Receive and parse the "init" event from the UI.
    message = await websocket.recv()
    event = json.loads(message)
    assert event["type"] == "init"

    if "join" in event:
        # Second player joins an existing game.
        await join(websocket, event["join"])
    elif "watch" in event:
        # Spectator watches an existing game.
        await watch(websocket, event["watch"])
    else:
        # First player starts a new game.
        await start(websocket)


""" async def handler(websocket):
    # Initialize a Connect Four game.
    game = Connect4()

    # Players take alternate turns, using the same browser.
    turns = itertools.cycle([PLAYER1, PLAYER2])
    player = next(turns)

    async for message in websocket:
        # Parse a "play" event from the UI.
        event = json.loads(message)
        assert event["type"] == "play"
        column = event["column"]

        try:
            # Play the move.
            row = game.play(player, column)
        except RuntimeError as exc:
            # Send an "error" event if the move was illegal.
            event = {
                "type": "error",
                "message": str(exc),
            }
            await websocket.send(json.dumps(event))
            continue

        # Send a "play" event to update the UI.
        event = {
            "type": "play",
            "player": player,
            "column": column,
            "row": row,
        }
        await websocket.send(json.dumps(event))

        # If move is winning, send a "win" event.
        if game.winner is not None:
            event = {
                "type": "win",
                "player": game.winner,
            }
            await websocket.send(json.dumps(event))

        # Alternate turns.
        player = next(turns)
 """

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())