#!/usr/bin/env python3
"""
Minimal Lichess Bot that plays with Stockfish.

Requires:
  pip install berserk python-chess requests

Env vars you must set before running:
  LICHESS_TOKEN   -> your Lichess API token (from a BOT account, with bot:play scope)
  STOCKFISH_PATH  -> full path to stockfish executable, e.g. C:/stockfish/stockfish.exe

Run:
  python bot.py
"""

import os
import traceback
from typing import Optional

import berserk
import chess
import chess.engine


# ------------ CONFIG ------------
ACCEPT_RATED = False             # Set True to allow rated games
ACCEPT_VARIANTS = {"standard"}   # e.g., {"standard", "chess960"}
MAX_GAME_BASETIME_SEC = 900      # Accept base time <= 5 minutes
MAX_GAME_INCREMENT_SEC = 10       # Accept increment <= 5 seconds

DEFAULT_THINK_TIME_SEC = 0.2     # Used when no/unknown clock times
MOVE_OVERHEAD_SEC = 0.05         # Safety buffer

USE_PONDER = False               # Keep it simple for now

# Stockfish tuning
STOCKFISH_THREADS = os.cpu_count() or 4
STOCKFISH_HASH_MB = 1024
STOCKFISH_SKILL_LEVEL = 20       # 0..20
# --------------------------------


def env(name: str, required: bool = True) -> Optional[str]:
    val = os.getenv(name)
    if required and (val is None or not val.strip()):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val


class LichessStockfishBot:
    def __init__(self):
        token = env("LICHESS_TOKEN")
        sf_path_raw = env("STOCKFISH_PATH")

        # Normalize Windows-quoted paths like "C:\path\stockfish.exe"
        sf_path = sf_path_raw.strip().strip('"').strip("'")
        sf_path = sf_path.replace("\\", "/")  # avoid \U escapes on Windows

        if not os.path.isfile(sf_path):
            raise RuntimeError(f"STOCKFISH_PATH does not point to a file: {sf_path}")

        # Lichess API session/client
        session = berserk.TokenSession(token)
        self.client = berserk.Client(session=session)

        # Ensure we are a Bot.
        me = self.client.account.get()
        if not (me.get("bot") or me.get("title") == "BOT"):
            raise RuntimeError(
                f"Account {me.get('username')} is not a Bot. Upgrade first and use a token with bot:play."
            )
        self.my_id = me.get("id")
        self.my_username = me.get("username")

        # Stockfish engine
        self.engine_path = sf_path
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        try:
            self.engine.configure({
                "Threads": STOCKFISH_THREADS,
                "Hash": STOCKFISH_HASH_MB,
                "Skill Level": STOCKFISH_SKILL_LEVEL,
            })
        except Exception:
            # Some builds use slightly different option names; ignore if not supported.
            pass

        print(f"Logged in as {self.my_username} ({self.my_id}). Engine at: {self.engine_path}")

    # -------- Challenge handling --------
    def should_accept(self, ch: dict) -> bool:
        try:
            if ch.get("challenger", {}).get("id") == self.my_id:
                return False  # ignore self-challenges

            if ch.get("variant", {}).get("key") not in ACCEPT_VARIANTS:
                return False

            if ch.get("rated", False) and not ACCEPT_RATED:
                return False

            tc = ch.get("timeControl", {})
            if tc.get("type") != "clock":
                return False
            base = int(tc.get("limit", 0))
            inc = int(tc.get("increment", 0))
            if base > MAX_GAME_BASETIME_SEC or inc > MAX_GAME_INCREMENT_SEC:
                return False

            return True
        except Exception:
            traceback.print_exc()
            return False

    def handle_event_stream(self):
        print("Starting event stream...")
        for event in self.client.bots.stream_incoming_events():
            t = event.get("type")

            if t == "challenge":
                ch = event.get("challenge", {})
                ch_id = ch.get("id")
                try:
                    if self.should_accept(ch):
                        print(f"Accepting challenge {ch_id}: {ch.get('challenger', {}).get('name')} / {ch.get('timeControl')}")
                        self.client.bots.accept_challenge(ch_id)
                    else:
                        print(f"Declining challenge {ch_id}")
                        self.client.bots.decline_challenge(ch_id)
                except Exception:
                    print(f"Error responding to challenge {ch_id}")
                    traceback.print_exc()

            elif t == "gameStart":
                game_id = event.get("game", {}).get("id")
                print(f"Game started: {game_id}")
                try:
                    self.play_game(game_id)
                except Exception:
                    print(f"Fatal error in game {game_id}")
                    traceback.print_exc()

            # "gameFinish" events are informational; nothing to do.

    # -------- Game loop --------
    def play_game(self, game_id: str):
        board = chess.Board()
        my_color = None  # True=white, False=black

        stream = self.client.bots.stream_game_state(game_id)

        for msg in stream:
            t = msg.get("type")

            if t == "gameFull":
                # Initial snapshot
                white_id = msg.get("white", {}).get("id")
                black_id = msg.get("black", {}).get("id")
                if white_id == self.my_id:
                    my_color = True
                elif black_id == self.my_id:
                    my_color = False

                moves_str = msg.get("state", {}).get("moves", "")
                self._apply_moves(board, moves_str)

                last = moves_str.split()[-1] if moves_str else "(start)"
                print(f"[{game_id}] gameFull | last: {last} | turn: {'white' if board.turn else 'black'}")

                # If it's our turn immediately (we are white), move now
                if my_color is not None and board.turn == my_color:
                    self._maybe_make_move(game_id, board, msg.get("state", {}), my_color)

            elif t == "gameState":
                # Subsequent updates: new moves & clock times
                moves_str = msg.get("moves", "")
                board = chess.Board()  # rebuild from scratch for safety
                self._apply_moves(board, moves_str)

                last = moves_str.split()[-1] if moves_str else "(start)"
                print(f"[{game_id}] gameState | last: {last} | turn: {'white' if board.turn else 'black'}")

                if my_color is not None and board.turn == my_color:
                    self._maybe_make_move(game_id, board, msg, my_color)

            elif t == "chatLine":
                # Optional: respond to chat if you like
                pass

        print(f"Game stream for {game_id} ended.")

    def _apply_moves(self, board: chess.Board, moves_str: str):
        if not moves_str:
            return
        for uci in moves_str.split():
            try:
                board.push_uci(uci)
            except Exception:
                traceback.print_exc()

    # -------- Time & phase helpers --------
    def _to_ms(self, v) -> int:
        """Best-effort convert Lichess time fields to milliseconds; return 0 if unknown."""
        try:
            if v is None:
                return 0
            if isinstance(v, (int, float)):
                return int(v)
            if isinstance(v, str):
                return int(float(v))  # handles "12345" and "12345.0"
            # Some berserk versions may yield datetime objects for timestamps; not usable as remaining time.
            import datetime
            if isinstance(v, datetime.datetime):
                return 0
            return 0
        except Exception:
            return 0

    def _is_endgame(self, board: chess.Board) -> bool:
        """Cheap endgame heuristic: no queens OR few non-pawn pieces remain."""
        pieces = board.piece_map().values()
        queens = sum(1 for p in pieces if p.piece_type == chess.QUEEN)
        non_pawn = sum(1 for p in board.piece_map().values()
                       if p.piece_type in (chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.QUEEN))
        return queens == 0 or non_pawn <= 4

    def _maybe_make_move(self, game_id: str, board: chess.Board, state_msg: dict, my_color: bool):
        # Extract remaining times (ms) if present, robust to types
        wtime_ms = self._to_ms(state_msg.get("wtime"))
        btime_ms = self._to_ms(state_msg.get("btime"))

        my_time_ms = wtime_ms if my_color else btime_ms
        think = self._choose_think_time(board, my_time_ms)

        try:
            limit = chess.engine.Limit(time=think)
            result = self.engine.play(board, limit, info=chess.engine.INFO_NONE, ponder=USE_PONDER)
            move = result.move
            if move is None:
                print(f"[{game_id}] No legal move (game likely over).")
                return

            print(f"[{game_id}] engine move: {move.uci()}  | think={think:.3f}s  | my_time_ms={my_time_ms}")
            self.client.bots.make_move(game_id, move.uci())
            # Ponder handling omitted for simplicity
        except chess.engine.EngineTerminatedError:
            print("Engine terminated unexpectedly. Restarting...")
            self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        except Exception:
            traceback.print_exc()

    def _choose_think_time(self, board: chess.Board, my_time_ms: int) -> float:
        if not my_time_ms or my_time_ms <= 0:
            return DEFAULT_THINK_TIME_SEC

        secs = my_time_ms / 1000.0
        base = max(0.02, min(0.5, secs / 40.0))  # ~2.5% of remaining time, clamped

        if self._is_endgame(board):
            base *= 0.7

        return max(0.02, base - MOVE_OVERHEAD_SEC)

    def run(self):
        try:
            self.handle_event_stream()
        finally:
            try:
                self.engine.quit()
            except Exception:
                pass


if __name__ == "__main__":
    bot = LichessStockfishBot()
    bot.run()
