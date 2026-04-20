import chess
import eval
import syzygy

DEPTH = 5
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
LMR_START_MOVE_INDEX = 3

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

    if is_maximizing:
        node_score = float("-inf")
        best_local_move = None

        for move_index, move in enumerate(legal_moves):
            is_quiet = (not move.promotion) and (not board.is_capture(move))
            can_reduce = (
                use_lmr
                and depth >= LMR_MIN_DEPTH
                and move_index >= LMR_START_MOVE_INDEX
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


def search(board, use_tt=True, use_null=False, use_lmr=True, reset_tt=False, verbose=False):
    global nodes_evaluated, tt_hits, null_move_cutoffs, lmr_reductions
    nodes_evaluated = 0
    tt_hits = 0
    null_move_cutoffs = 0
    lmr_reductions = 0

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

    tt_move = None
    if use_tt:
        root_entry = transposition_table.get(board_key(board))
        if root_entry:
            tt_move = root_entry["best_move"]

    legal_moves = order_root_moves(board, tt_move=tt_move)
    best_move = None
    best_score = float("-inf") if board.turn == chess.WHITE else float("inf")

    for move in legal_moves:
        board.push(move)
        score = minimax(
            board,
            DEPTH - 1,
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

        if board.turn == chess.WHITE:
            if score > best_score:
                best_score = score
                best_move = move
        else:
            if score < best_score:
                best_score = score
                best_move = move

    if verbose:
        print(
            f"Best move: {best_move}, Best score: {best_score}, "
            f"Nodes evaluated: {nodes_evaluated}, TT hits: {tt_hits}, "
            f"Null cutoffs: {null_move_cutoffs}, LMR reductions: {lmr_reductions}"
        )
        print(f"Board evaluation: {eval.evaluate(board)}")

    return best_move




