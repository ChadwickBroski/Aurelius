import chess
import eval
import syzygy
import sys
import time

DEPTH = 4
nodes_evaluated = 0
tt_hits = 0
null_move_cutoffs = 0
lmr_reductions = 0

PIECE_VALUES = {
    chess.PAWN: 10,
    chess.KNIGHT: 30,
    chess.BISHOP: 30,
    chess.ROOK: 50,
    chess.QUEEN: 90,
    chess.KING: 0,
}

killer_moves = {}
transposition_table = {}

TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2
TT_MAX_ENTRIES = 200000

NULL_MOVE_MIN_DEPTH = 3
LMR_MIN_DEPTH = 3
LMR_START_MOVE_INDEX = 4
LMR_MIN_LEGAL_MOVES = 8
ROOT_CHECKMATE_SCORE = 1000000
EVAL_CHECKMATE_SCORE = 10000000

# Safety multiplier used by iterative deepening to decide whether there's
# time for one more (deeper) iteration. With decent move ordering and
# pruning, each extra ply tends to cost somewhere around 2-6x the previous
# one - 5x is a conservative middle-of-that-range guess, not a measured
# value. It only affects whether ID *starts* a deeper search in time; it
# can't interrupt a search that's already in progress (see search()).
ID_NEXT_DEPTH_TIME_MULTIPLIER = 5


def board_key(board):
    # python-chess exposes a private but fast transposition key.
    if hasattr(board, "_transposition_key"):
        return board._transposition_key()
    return board.fen()


def gives_check_fast(board, move):
    if hasattr(board, "gives_check"):
        return board.gives_check(move)

    board.push(move)
    is_check = board.is_check()
    board.pop()
    return is_check


def has_non_pawn_material(board, color):
    return bool(
        board.pieces(chess.KNIGHT, color)
        or board.pieces(chess.BISHOP, color)
        or board.pieces(chess.ROOK, color)
        or board.pieces(chess.QUEEN, color)
    )


def store_tt_entry(tt_key, depth, score, flag, best_move):
    if tt_key is None:
        return

    if len(transposition_table) >= TT_MAX_ENTRIES:
        transposition_table.clear()

    transposition_table[tt_key] = {
        "depth": depth,
        "score": score,
        "flag": flag,
        "best_move": best_move,
    }


def capture_score(board, move):
    attacker = board.piece_at(move.from_square)
    victim = board.piece_at(move.to_square)
    attacker_value = PIECE_VALUES.get(attacker.piece_type, 0) if attacker else 0
    victim_value = PIECE_VALUES.get(victim.piece_type, PIECE_VALUES[chess.PAWN]) if victim else PIECE_VALUES[chess.PAWN]
    return victim_value * 10 - attacker_value


def root_move_order_score(board, move):
    score = 0

    if move.promotion:
        score += 800 + PIECE_VALUES.get(move.promotion, 0)

    if board.is_capture(move):
        score += 1000 + capture_score(board, move)

    if gives_check_fast(board, move):
        score += 150

    return score


def inner_move_order_score(board, move):
    score = 0

    if move.promotion:
        score += 800 + PIECE_VALUES.get(move.promotion, 0)

    if board.is_capture(move):
        score += 1000 + capture_score(board, move)

    return score


def order_root_moves(board, tt_move=None):
    moves = list(board.legal_moves)
    moves.sort(key=lambda move: root_move_order_score(board, move), reverse=True)

    if tt_move in moves:
        moves.remove(tt_move)
        moves.insert(0, tt_move)

    return moves


def order_inner_moves(board, depth, tt_move=None):
    tactical = []
    quiet = []

    for move in board.legal_moves:
        if move.promotion or board.is_capture(move):
            tactical.append((inner_move_order_score(board, move), move))
        else:
            quiet.append(move)

    tactical.sort(key=lambda item: item[0], reverse=True)

    killer = killer_moves.get(depth)
    if killer in quiet:
        quiet.remove(killer)
        quiet.insert(0, killer)

    ordered = [move for _, move in tactical] + quiet

    if tt_move in ordered:
        ordered.remove(tt_move)
        ordered.insert(0, tt_move)

    return ordered


def minimax(
    board,
    depth,
    alpha,
    beta,
    is_maximizing,
    use_tt=True,
    use_null=False,
    use_lmr=True,
    allow_null=True,
):
    global nodes_evaluated, tt_hits, null_move_cutoffs, lmr_reductions
    nodes_evaluated += 1

    if depth == 0 or board.is_game_over():
        return eval.evaluate(board)

    # Check if we can use syzygy tablebase for endgames
    piece_count = syzygy.get_piece_count(board)
    if piece_count <= 7:
        syzygy_move = syzygy.get_syzygy_move(board)
        if syzygy_move is not None:
            # Syzygy found a move, evaluate it and use it directly
            board.push(syzygy_move)
            score = minimax(
                board, depth - 1, alpha, beta, not is_maximizing,
                use_tt=use_tt, use_null=use_null, use_lmr=use_lmr, allow_null=True
            )
            board.pop()
            return score

    alpha_original = alpha
    beta_original = beta
    tt_key = None
    tt_move = None
    tt_entry = None

    if use_tt:
        tt_key = board_key(board)
        tt_entry = transposition_table.get(tt_key)

        if tt_entry and tt_entry["depth"] >= depth:
            tt_hits += 1
            score = tt_entry["score"]
            flag = tt_entry["flag"]

            if flag == TT_EXACT:
                return score
            if flag == TT_LOWER:
                alpha = max(alpha, score)
            else:
                beta = min(beta, score)

            if alpha >= beta:
                return score

        if tt_entry:
            tt_move = tt_entry["best_move"]

    if (
        use_null
        and allow_null
        and depth >= NULL_MOVE_MIN_DEPTH
        and not board.is_check()
        and has_non_pawn_material(board, board.turn)
    ):
        reduction = 2 if depth >= 6 else 1
        null_depth = depth - 1 - reduction

        if null_depth >= 0:
            board.push(chess.Move.null())
            null_score = minimax(
                board,
                null_depth,
                alpha,
                beta,
                not is_maximizing,
                use_tt=use_tt,
                use_null=use_null,
                use_lmr=use_lmr,
                allow_null=False,
            )
            board.pop()

            if is_maximizing and null_score >= beta:
                null_move_cutoffs += 1
                if use_tt:
                    store_tt_entry(tt_key, depth, null_score, TT_LOWER, None)
                return null_score

            if (not is_maximizing) and null_score <= alpha:
                null_move_cutoffs += 1
                if use_tt:
                    store_tt_entry(tt_key, depth, null_score, TT_UPPER, None)
                return null_score

    legal_moves = order_inner_moves(board, depth, tt_move=tt_move)
    legal_move_count = len(legal_moves)

    if is_maximizing:
        node_score = float("-inf")
        best_local_move = None

        for move_index, move in enumerate(legal_moves):
            is_quiet = (not move.promotion) and (not board.is_capture(move))
            can_reduce = (
                use_lmr
                and depth >= LMR_MIN_DEPTH
                and move_index >= LMR_START_MOVE_INDEX
                and legal_move_count >= LMR_MIN_LEGAL_MOVES
                and is_quiet
                and not board.is_check()
            )

            if can_reduce:
                lmr_reductions += 1

                board.push(move)
                value = minimax(
                    board,
                    depth - 2,
                    alpha,
                    beta,
                    False,
                    use_tt=use_tt,
                    use_null=use_null,
                    use_lmr=use_lmr,
                    allow_null=True,
                )
                board.pop()

                if value > alpha:
                    board.push(move)
                    value = minimax(
                        board,
                        depth - 1,
                        alpha,
                        beta,
                        False,
                        use_tt=use_tt,
                        use_null=use_null,
                        use_lmr=use_lmr,
                        allow_null=True,
                    )
                    board.pop()
            else:
                board.push(move)
                value = minimax(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    False,
                    use_tt=use_tt,
                    use_null=use_null,
                    use_lmr=use_lmr,
                    allow_null=True,
                )
                board.pop()

            if value > node_score:
                node_score = value
                best_local_move = move

            alpha = max(alpha, value)
            if beta <= alpha:
                killer_moves[depth] = move
                break

    else:
        node_score = float("inf")
        best_local_move = None

        for move_index, move in enumerate(legal_moves):
            is_quiet = (not move.promotion) and (not board.is_capture(move))
            can_reduce = (
                use_lmr
                and depth >= LMR_MIN_DEPTH
                and move_index >= LMR_START_MOVE_INDEX
                and legal_move_count >= LMR_MIN_LEGAL_MOVES
                and is_quiet
                and not board.is_check()
            )

            if can_reduce:
                lmr_reductions += 1

                board.push(move)
                value = minimax(
                    board,
                    depth - 2,
                    alpha,
                    beta,
                    True,
                    use_tt=use_tt,
                    use_null=use_null,
                    use_lmr=use_lmr,
                    allow_null=True,
                )
                board.pop()

                if value < beta:
                    board.push(move)
                    value = minimax(
                        board,
                        depth - 1,
                        alpha,
                        beta,
                        True,
                        use_tt=use_tt,
                        use_null=use_null,
                        use_lmr=use_lmr,
                        allow_null=True,
                    )
                    board.pop()
            else:
                board.push(move)
                value = minimax(
                    board,
                    depth - 1,
                    alpha,
                    beta,
                    True,
                    use_tt=use_tt,
                    use_null=use_null,
                    use_lmr=use_lmr,
                    allow_null=True,
                )
                board.pop()

            if value < node_score:
                node_score = value
                best_local_move = move

            beta = min(beta, value)
            if beta <= alpha:
                killer_moves[depth] = move
                break

    if use_tt and tt_key is not None:
        if node_score <= alpha_original:
            flag = TT_UPPER
        elif node_score >= beta_original:
            flag = TT_LOWER
        else:
            flag = TT_EXACT

        store_tt_entry(tt_key, depth, node_score, flag, best_local_move)

    return node_score


def search_fixed_depth(board, search_depth, use_tt=True, use_null=False, use_lmr=True, verbose=False):
    """Run a single fixed-depth root search (the original search() body,
    factored out so iterative deepening can call it once per depth).

    Returns (best_move, best_score, forced_mate_found).
    """
    root_turn = board.turn

    tt_move = None
    if use_tt:
        root_entry = transposition_table.get(board_key(board))
        if root_entry:
            tt_move = root_entry["best_move"]

    legal_moves = order_root_moves(board, tt_move=tt_move)
    best_move = None
    best_score = float("-inf") if root_turn == chess.WHITE else float("inf")

    for move in legal_moves:
        board.push(move)
        if board.is_checkmate():
            board.pop()
            score = ROOT_CHECKMATE_SCORE if root_turn == chess.WHITE else -ROOT_CHECKMATE_SCORE
            if verbose:
                print(f"Move: {move}, Score: {score}")
                print(f"Immediate checkmate found. Playing: {move}")
            return move, score, True

        score = minimax(
            board,
            search_depth - 1,
            float("-inf"),
            float("inf"),
            board.turn == chess.WHITE,
            use_tt=use_tt,
            use_null=use_null,
            use_lmr=use_lmr,
            allow_null=True,
        )
        board.pop()

        if verbose:
            print(f"Move: {move}, Score: {score}")

        # If search already found a forced mate, no need to inspect other root moves.
        if root_turn == chess.WHITE and score >= EVAL_CHECKMATE_SCORE:
            if verbose:
                print(f"Forced checkmate found. Playing: {move}")
            return move, score, True
        if root_turn == chess.BLACK and score <= -EVAL_CHECKMATE_SCORE:
            if verbose:
                print(f"Forced checkmate found. Playing: {move}")
            return move, score, True

        if root_turn == chess.WHITE:
            if score > best_score:
                best_score = score
                best_move = move
        else:
            if score < best_score:
                best_score = score
                best_move = move

    return best_move, best_score, False


def search(board, use_tt=True, use_null=False, use_lmr=True, reset_tt=False, verbose=False, depth=DEPTH, uci_output=False, max_time=None):
    """
    Two modes, controlled by max_time:

    - max_time=None (default): exactly the original behavior - a single
      fixed-depth search at `depth`. Nothing about this path changed;
      existing callers (like predict_reply) are unaffected.

    - max_time=<seconds>: iterative deepening. Searches depth 1, then 2,
      then 3, ... printing a UCI "info depth ..." line after each one
      completes, using each depth's best move to seed move ordering for
      the next (via the transposition table) and stopping once there's
      no longer time for another full iteration, or `depth` is reached.
      Returns the best move from the deepest iteration that finished.

    Note: this can't interrupt a search that's already in progress -
    minimax has no time-check hook threaded through its recursion, so if
    a single iteration itself runs long (e.g. a very tactical position),
    it will still be allowed to finish. The time budget only governs
    whether a *new* iteration is started, not whether an in-progress one
    is cut short.
    """
    global nodes_evaluated, tt_hits, null_move_cutoffs, lmr_reductions
    start_time = time.perf_counter()

    # Check for syzygy tablebase move in endgames (7 or fewer pieces)
    piece_count = syzygy.get_piece_count(board)
    if piece_count <= 7:
        syzygy_move = syzygy.get_syzygy_move(board)
        if syzygy_move is not None:
            if verbose:
                print(f"Using Syzygy tablebase move: {syzygy_move}")
                print(f"Piece count: {piece_count}")
            return syzygy_move

    if reset_tt:
        transposition_table.clear()

    max_depth = max(1, depth)
    best_move = None
    best_score = None
    if max_time is None:
        # Fixed-depth mode: exactly one search, directly at the requested
        # depth - no iteration. (Previously this incorrectly looped
        # starting from depth 1 and broke after that first iteration,
        # meaning fixed-depth mode always searched depth 1 regardless of
        # what depth was actually requested - that's fixed here.)
        nodes_evaluated = 0
        tt_hits = 0
        null_move_cutoffs = 0
        lmr_reductions = 0

        depth_start = time.perf_counter()
        best_move, best_score, forced_mate = search_fixed_depth(
            board, max_depth, use_tt=use_tt, use_null=use_null, use_lmr=use_lmr, verbose=verbose
        )
        depth_elapsed = time.perf_counter() - depth_start
        total_elapsed = time.perf_counter() - start_time

        if uci_output and best_move is not None:
            nps = int(nodes_evaluated / depth_elapsed) if depth_elapsed > 0.001 else 0
            cp = int(max(-100000, min(100000, best_score)))
            pv = best_move.uci()
            print(f"info depth {max_depth} score cp {cp} nodes {nodes_evaluated} nps {nps} time {int(total_elapsed * 1000)} pv {pv}")
            sys.stdout.flush()

        if verbose:
            print(f"Board evaluation: {eval.evaluate(board)}")

        return best_move

    # Iterative deepening mode: search depth 1, 2, 3, ... until the time
    # budget runs out or max_depth is reached.
    current_depth = 1

    while current_depth <= max_depth:
        nodes_evaluated = 0
        tt_hits = 0
        null_move_cutoffs = 0
        lmr_reductions = 0

        depth_start = time.perf_counter()
        move, score, forced_mate = search_fixed_depth(
            board, current_depth, use_tt=use_tt, use_null=use_null, use_lmr=use_lmr, verbose=verbose
        )
        depth_elapsed = time.perf_counter() - depth_start
        total_elapsed = time.perf_counter() - start_time

        if move is not None:
            best_move = move
            best_score = score

        if uci_output and best_move is not None:
            nps = int(nodes_evaluated / depth_elapsed) if depth_elapsed > 0.001 else 0
            # Clamp score away from inf/-inf (checkmate scores)
            cp = int(max(-100000, min(100000, best_score)))
            pv = best_move.uci()
            print(f"info depth {current_depth} score cp {cp} nodes {nodes_evaluated} nps {nps} time {int(total_elapsed * 1000)} pv {pv}")
            sys.stdout.flush()

        if verbose:
            print(
                f"Depth {current_depth} complete - Best move: {best_move}, Best score: {best_score}, "
                f"Nodes evaluated: {nodes_evaluated}, TT hits: {tt_hits}, "
                f"Null cutoffs: {null_move_cutoffs}, LMR reductions: {lmr_reductions}, "
                f"Depth time: {depth_elapsed:.3f}s, Total time: {total_elapsed:.3f}s"
            )

        if forced_mate:
            break

        remaining_time = max_time - total_elapsed
        projected_next_depth_time = depth_elapsed * ID_NEXT_DEPTH_TIME_MULTIPLIER

        if remaining_time <= 0 or projected_next_depth_time > remaining_time:
            break

        current_depth += 1

    if verbose:
        print(f"Board evaluation: {eval.evaluate(board)}")

    return best_move


def ponder(board, guess_depth=2, ponder_depth=None, ponder_time=None, use_null=False, use_lmr=True, verbose=False):
    """
    Use idle time - after we've played our move, while waiting for the
    opponent's actual move - to guess their most likely reply and search
    that resulting position now, with the transposition table ENABLED.

    This is different from predict_reply(), which deliberately runs with
    use_tt=False and restores killer_moves afterward, since it exists
    purely to print a debug guess without touching shared search state.
    ponder() does the opposite on purpose: it WANTS the transposition
    table and killer_moves to end up populated with real analysis of the
    guessed position, so that if the opponent actually plays that move,
    the next real search finds cached entries already sitting there
    (at whatever depth this pondering reached) instead of starting cold.
    That's what makes the following search faster/deeper for the same
    time budget as the game goes on.

    If the opponent plays something other than the guessed move, this
    was wasted work - normal, expected tradeoff with pondering in any
    engine, not a bug. Positions that never actually occur just sit
    unused in the transposition table until they're naturally evicted.

    guess_depth: how deep to search just to pick a plausible reply -
                 shallow and fast, it only needs a decent guess, not the
                 strongest possible move (deeper guessing eats into the
                 time actually spent analyzing the guessed position).
    ponder_depth / ponder_time: how much of the idle-time budget to
                 spend analyzing the guessed position - same semantics
                 as search()'s depth/max_time. If ponder_time is given
                 and ponder_depth isn't, defaults to a high cap (99) so
                 max_time is what actually limits it, matching how
                 iterative deepening is used elsewhere in this file.

    Returns the guessed move (useful for logging/verbose output), or
    None if the position is already game-over. Does not modify `board`.
    Restores nodes_evaluated/tt_hits/null_move_cutoffs/lmr_reductions
    afterward, so this speculative work doesn't get mixed into the
    stats for the real move that was just played and printed.
    """
    global nodes_evaluated, tt_hits, null_move_cutoffs, lmr_reductions

    if board.is_game_over():
        return None

    saved_nodes_evaluated = nodes_evaluated
    saved_tt_hits = tt_hits
    saved_null_move_cutoffs = null_move_cutoffs
    saved_lmr_reductions = lmr_reductions

    try:
        ponder_board = board.copy(stack=False)

        # Quick, shallow search just to guess a plausible reply.
        guessed_move = search(
            ponder_board,
            use_tt=True,
            use_null=use_null,
            use_lmr=use_lmr,
            depth=guess_depth,
            verbose=False,
        )

        if guessed_move is None:
            return None

        ponder_board.push(guessed_move)

        if ponder_board.is_game_over():
            return guessed_move

        effective_depth = ponder_depth
        if effective_depth is None:
            effective_depth = 99 if ponder_time is not None else DEPTH

        # The real work: analyze the guessed position and let its
        # results land in the shared transposition_table (use_tt=True,
        # not restored in `finally` below - that's the whole point).
        search(
            ponder_board,
            use_tt=True,
            use_null=use_null,
            use_lmr=use_lmr,
            depth=effective_depth,
            max_time=ponder_time,
            verbose=verbose,
        )

        return guessed_move
    finally:
        nodes_evaluated = saved_nodes_evaluated
        tt_hits = saved_tt_hits
        null_move_cutoffs = saved_null_move_cutoffs
        lmr_reductions = saved_lmr_reductions


def predict_reply(board, depth=DEPTH, use_null=False, use_lmr=True, verbose=False):
    """Return the opponent's likely best reply without changing normal search state."""
    global nodes_evaluated, tt_hits, null_move_cutoffs, lmr_reductions, killer_moves

    saved_nodes_evaluated = nodes_evaluated
    saved_tt_hits = tt_hits
    saved_null_move_cutoffs = null_move_cutoffs
    saved_lmr_reductions = lmr_reductions
    saved_killer_moves = killer_moves.copy()

    try:
        return search(
            board.copy(stack=False),
            use_tt=False,
            use_null=use_null,
            use_lmr=use_lmr,
            reset_tt=False,
            verbose=verbose,
            depth=depth,
        )
    finally:
        nodes_evaluated = saved_nodes_evaluated
        tt_hits = saved_tt_hits
        null_move_cutoffs = saved_null_move_cutoffs
        lmr_reductions = saved_lmr_reductions
        killer_moves = saved_killer_moves
