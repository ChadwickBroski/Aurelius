import chess
import chess.pgn
import search
import time


MAX_PLIES = 200


def make_starting_board():
    return chess.Board()


def game_over_reason(board, reached_max_plies):
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"Checkmate. {winner} wins."
    if board.is_stalemate():
        return "Draw by stalemate."
    if board.is_insufficient_material():
        return "Draw by insufficient material."
    if board.is_seventyfive_moves():
        return "Draw by seventy-five-move rule."
    if board.is_fivefold_repetition():
        return "Draw by fivefold repetition."
    if board.can_claim_fifty_moves():
        return "Draw claim available by fifty-move rule."
    if board.can_claim_threefold_repetition():
        return "Draw claim available by threefold repetition."
    if reached_max_plies:
        return f"Stopped after {MAX_PLIES} plies."
    if board.is_game_over():
        return "Game over."
    return "Simulation stopped."


def ask_depth():
    while True:
        raw_depth = input("Search depth for self-play: ").strip()
        try:
            depth = int(raw_depth)
        except ValueError:
            print("Please enter a whole number.")
            continue

        if depth < 1:
            print("Depth must be at least 1.")
            continue

        return depth


def ask_confirmation(depth):
    print(f"Self-play will start from the default board at depth {depth}.")
    answer = input("Start simulation? Type 'yes' to confirm: ").strip().lower()
    return answer == "yes"


def play_self_game(depth):
    board = make_starting_board()
    game = chess.pgn.Game()
    game.headers["Event"] = "Aurelius Debug Self-Play"
    game.headers["Site"] = "Local"
    game.headers["White"] = "Aurelius"
    game.headers["Black"] = "Aurelius"
    game.setup(board)
    node = game
    ply = 0

    print()
    print(board)

    while not board.is_game_over() and ply < MAX_PLIES:
        side = "White" if board.turn == chess.WHITE else "Black"
        start_time = time.perf_counter()
        move = search.search(board, depth=depth, verbose=True)
        elapsed = time.perf_counter() - start_time

        if move is None:
            print(f"{side} has no move. Stopping simulation.")
            break

        san = board.san(move)
        node = node.add_variation(move)
        board.push(move)
        ply += 1

        print()
        print(f"{ply}. {side} plays {san} ({move}) in {elapsed:.3f}s")
        print(board)

    print()
    reason = game_over_reason(board, ply >= MAX_PLIES)
    print(f"{reason} Result: {board.result(claim_draw=True)}")

    game.headers["Result"] = board.result(claim_draw=True)
    print()
    print("Final PGN:")
    print(game)


def main():
    depth = ask_depth()
    if not ask_confirmation(depth):
        print("Simulation cancelled.")
        return

    play_self_game(depth)


if __name__ == "__main__":
    main()
