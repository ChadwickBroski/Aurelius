import sys
import os
import chess

import search
from opening_book import OpeningBook

ENGINE_NAME = "Aurelius"
ENGINE_AUTHOR = "ChadwickBroski [GITHUB]"

OPENING_BOOK_PATH = os.path.join(os.path.dirname(__file__), "openings", "openings.json")

# Depth cap passed to search.search() when we're in iterative-deepening
# mode (movetime/wtime/btime). It's not really a target - max_time is
# what actually limits the search - it just stops ID from looping forever
# in the (very unlikely) case a time budget is huge and positions are
# simple enough to hit very deep iterations quickly.
MAX_ITERATIVE_DEPTH = 99


def parse_position(command: str, board: chess.Board) -> chess.Board:
    """
    Support:
      position startpos
      position startpos moves e2e4 e7e5
      position fen <fen...>
      position fen <fen...> moves ...
    """
    parts = command.strip().split()
    if len(parts) < 2:
        return board

    idx = 1

    if parts[idx] == "startpos":
        board = chess.Board()
        idx += 1

    elif parts[idx] == "fen":
        fen_parts = []
        idx += 1
        while idx < len(parts) and parts[idx] != "moves":
            fen_parts.append(parts[idx])
            idx += 1

        fen = " ".join(fen_parts)
        try:
            board = chess.Board(fen)
        except Exception:
            # Keep the current board if the GUI sends a malformed FEN.
            return board

    else:
        return board

    if idx < len(parts) and parts[idx] == "moves":
        idx += 1
        while idx < len(parts):
            move_str = parts[idx]
            try:
                board.push_uci(move_str)
            except Exception:
                break
            idx += 1

    return board


def parse_go(command: str, board: chess.Board) -> dict:
    """
    Parse a UCI 'go' command into search parameters.

    Returns a dict: {"depth": <int or None>, "max_time": <float seconds or None>}

    Supports:
      go depth 5              -> fixed depth, no time limit (old behavior)
      go movetime 1000        -> iterative deepening, ~1000ms budget
      go wtime .. btime ..    -> iterative deepening, budget computed from
                                  the side-to-move's remaining clock
      (anything else/no args) -> fixed depth at the engine default

    Note: 'go infinite' isn't specially handled - it falls through to the
    same default as a bare 'go', same as before this change.
    """
    parts = command.split()

    if "depth" in parts:
        try:
            depth = max(1, int(parts[parts.index("depth") + 1]))
            return {"depth": depth, "max_time": None}
        except Exception:
            pass

    if "movetime" in parts:
        try:
            ms = int(parts[parts.index("movetime") + 1])
            return {"depth": MAX_ITERATIVE_DEPTH, "max_time": max(0.05, ms / 1000.0)}
        except Exception:
            pass

    if "wtime" in parts or "btime" in parts:
        try:
            def get_value(key):
                if key in parts:
                    return int(parts[parts.index(key) + 1])
                return None

            wtime = get_value("wtime")
            btime = get_value("btime")
            winc = get_value("winc") or 0
            binc = get_value("binc") or 0

            remaining_ms = wtime if board.turn == chess.WHITE else btime
            increment_ms = winc if board.turn == chess.WHITE else binc

            if remaining_ms is not None:
                # Simple time management, not tuned: budget ~1/30th of the
                # remaining clock (assumes roughly 30 moves left in the
                # game) plus most of the increment, since increment is
                # basically free - it gets added back after the move.
                # Capped at half of what's left and floored at 50ms so
                # neither extreme (very little time, or a huge increment)
                # produces a silly budget.
                budget_ms = (remaining_ms / 30.0) + (increment_ms * 0.8)
                budget_ms = min(budget_ms, remaining_ms * 0.5)
                budget_ms = max(budget_ms, 50)
                return {"depth": MAX_ITERATIVE_DEPTH, "max_time": budget_ms / 1000.0}
        except Exception:
            pass

    return {"depth": None, "max_time": None}


def choose_move(board: chess.Board, depth: int | None, max_time: float | None = None, opening_book: OpeningBook | None = None) -> chess.Move | None:
    try:
        # Try opening book first
        if opening_book is not None:
            book_move, opening_name, opening_san, book_status = opening_book.next_move(
                board, engine_color=board.turn
            )
            if book_move is not None:
                return book_move

        if depth is None:
            return search.search(board, verbose=False, uci_output=True, max_time=max_time)
        return search.search(board, verbose=False, depth=depth, uci_output=True, max_time=max_time)
    except Exception:
        return None


def main():
    board = chess.Board()
    search_depth = search.DEPTH
    opening_book = OpeningBook(OPENING_BOOK_PATH, enabled=True)

    while True:
        line = sys.stdin.readline()
        if not line:
            break

        command = line.strip()

        if not command:
            continue

        if command == "uci":
            print(f"id name {ENGINE_NAME}")
            print(f"id author {ENGINE_AUTHOR}")
            print("uciok")
            sys.stdout.flush()

        elif command == "isready":
            print("readyok")
            sys.stdout.flush()

        elif command == "ucinewgame":
            board = chess.Board()
            search.transposition_table.clear()
            search.killer_moves.clear()
            opening_book = OpeningBook(OPENING_BOOK_PATH, enabled=True)
            sys.stdout.flush()

        elif command.startswith("setoption"):
            # Ignore unknown options for now.
            sys.stdout.flush()

        elif command.startswith("position"):
            board = parse_position(command, board)
            sys.stdout.flush()

        elif command.startswith("go"):
            go_params = parse_go(command, board)
            depth = go_params["depth"]
            max_time = go_params["max_time"]
            if depth is None:
                depth = search_depth

            best_move = choose_move(board, depth, max_time, opening_book)

            if best_move is None:
                print("bestmove 0000")
            else:
                print(f"bestmove {best_move.uci()}")
            sys.stdout.flush()

        elif command == "stop":
            # This simple engine searches synchronously, so stop is a no-op.
            sys.stdout.flush()

        elif command == "quit":
            break

        # Non-UCI debug commands are ignored silently.


if __name__ == "__main__":
    main()