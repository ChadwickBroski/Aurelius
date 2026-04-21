import chess
import sys
import os
import search
import eval
import time
from chess import IllegalMoveError, InvalidMoveError, AmbiguousMoveError
from opening_book import OpeningBook

version = "0.1.1"
name = "Aurelius"
SEARCH_VERBOSE = True
USE_OPENING_BOOK = True
ENGINE_COLOR = chess.WHITE
OPENING_BOOK_PATH = os.path.join(os.path.dirname(__file__), "openings", "openings.json")

board = chess.Board()
opening_book = OpeningBook(OPENING_BOOK_PATH, enabled=USE_OPENING_BOOK)
current_opening_name = None


def parse_user_move_safely(board, raw_move):
    text = raw_move.strip()
    candidates = []

    def add(candidate):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add(text)

    # Accept 0-0 / 0-0-0 and lowercase castling forms.
    castle_normalized = text.replace("0", "O").replace("o", "O")
    add(castle_normalized)

    if text and text[0].isalpha():
        add(text[0].upper() + text[1:])
        add(text[0].upper() + text[1:].lower())
        add(text[0].lower() + text[1:].lower())

    # Common typo: lowercase bishop moves like "bd2".
    if text and text[0] in "abcdefgh" and len(text) >= 2 and text[1] in "abcdefgh":
        add(text[0].upper() + text[1:])
        add(text[0].upper() + text[1:].lower())

    last_error = None
    for candidate in candidates:
        try:
            return board.parse_san(candidate)
        except (IllegalMoveError, InvalidMoveError, AmbiguousMoveError, ValueError) as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise ValueError("Illegal move")


print(f"Playing with {name} {version}")
print(board)

if ENGINE_COLOR not in (chess.WHITE, chess.BLACK):
    print("Invalid ENGINE_COLOR. Use chess.WHITE or chess.BLACK.")
    sys.exit(1)

human_color = chess.BLACK if ENGINE_COLOR == chess.WHITE else chess.WHITE
print(f"{name} plays {'White' if ENGINE_COLOR == chess.WHITE else 'Black'}.")
print(f"You play {'White' if human_color == chess.WHITE else 'Black'}.")

terminated_early = False

while not board.is_game_over():
    if board.turn == ENGINE_COLOR:
        start_time = time.perf_counter()

        try:
            book_move, opening_name, opening_san, book_status = opening_book.next_move(
                board, engine_color=ENGINE_COLOR
            )

            if book_move is not None:
                comp_move = book_move
                if opening_name != current_opening_name:
                    current_opening_name = opening_name
            else:
                comp_move = search.search(board, verbose=SEARCH_VERBOSE)

            end_time = time.perf_counter() - start_time

            print(f"{name} plays: {comp_move}")
            board.push(comp_move)
            print(board)
        except Exception as e:
            print(f"Engine error: {e}")
            terminated_early = True
            break
    else:
        user_input = input("Your move: ").strip()

        if user_input.lower() == "quit":
            print("Exiting the game.")
            sys.exit()

        try:
            user_move = parse_user_move_safely(board, user_input)
            board.push(user_move)
            print(board)
        except (IllegalMoveError, InvalidMoveError, AmbiguousMoveError, ValueError):
            print("Illegal move")
        except Exception as e:
            print(f"Input error: {e}")

if not terminated_early:
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        print(f"{winner} wins!")
    else:
        print("Draw!")
