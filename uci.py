import sys
import os
import chess

import search
from opening_book import OpeningBook

ENGINE_NAME = "Aurelius"
ENGINE_AUTHOR = "ChadwickBroski [GITHUB]"

OPENING_BOOK_PATH = os.path.join(os.path.dirname(__file__), "openings", "openings.json")


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


def parse_go(command: str) -> int | None:
    """
    Return a search depth if provided, otherwise None.
    Supports:
      go depth 5
      go movetime 1000
    """
    parts = command.split()

    if "depth" in parts:
        try:
            return max(1, int(parts[parts.index("depth") + 1]))
        except Exception:
            return None

    if "movetime" in parts:
        try:
            ms = int(parts[parts.index("movetime") + 1])
            # Very simple conversion: roughly 1 ply per 250ms, minimum 1.
            return max(1, ms // 250)
        except Exception:
            return None

    return None


def choose_move(board: chess.Board, depth: int | None, opening_book: OpeningBook | None = None) -> chess.Move | None:
    try:
        # Try opening book first
        if opening_book is not None:
            book_move, opening_name, opening_san, book_status = opening_book.next_move(
                board, engine_color=board.turn
            )
            if book_move is not None:
                return book_move

        if depth is None:
            return search.search(board, verbose=False, uci_output=True)
        return search.search(board, verbose=False, depth=depth, uci_output=True)
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
            depth = parse_go(command)
            if depth is None:
                depth = search_depth

            best_move = choose_move(board, depth, opening_book)

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