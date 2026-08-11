import chess

def evaluate(board):

    score = 0

    # FIXED: removed board.is_repetition(2), which fires the moment a
    # position occurs twice - that happens constantly in normal play
    # (e.g. Nf3 Nf6 Ng1 Ng8) and is NOT a draw. Also dropped
    # can_claim_threefold_repetition() / can_claim_fifty_moves() /
    # is_fifty_moves(), since can_claim_draw() already re-checks
    # threefold repetition and the 50-move rule internally - keeping
    # them alongside it was just repeating the same expensive
    # move-stack replay for no extra information.
    if (board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or board.can_claim_draw()):
        return 0  # Draw
    
    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return -10000000  # Black wins
        return 10000000  # White wins
    
    # Simple evaluation function based on material count
    piece_values = {
        chess.PAWN: 10,
        chess.KNIGHT: 30,
        chess.BISHOP: 30,
        chess.ROOK: 50,
        chess.QUEEN: 90,
        chess.KING: 0
    }

    pawn_table = [
        [0,   0,   0,   0,   0,   0,   0,   0],
        [5,   5,   5,   5,   5,   5,   5,   5],
        [10,  10,  10,  10,  10,  10,  10,  10],
        [5,   5,  10,  20,  20,  10,   5,   5],
        [0,   0,   5,  15,  15,   5,   0,   0],
        [5,  -5,  -5,   0,   0,  -5,  -5,   5],
        [5,  10,  10, -20, -20,  10,  10,   5],
        [0,   0,   0,   0,   0,   0,   0,   0]
    ]

    knight_table = [
        [-50, -40, -30, -30, -30, -30, -40, -50],
        [-40, -20,   0,   5,   5,   0, -20, -40],
        [-30,   0,  10,  15,  15,  10,   0, -30],
        [-30,   5,  15,  20,  20,  15,   5, -30],
        [-30,   5,  15,  20,  20,  15,   5, -30],
        [-30,   0,  10,  15,  15,  10,   0, -30],
        [-40, -20,   0,   5,   5,   0, -20, -40],
        [-50, -40, -30, -30, -30, -30, -40, -50]
    ]

    # NOTE: fixed a stray -20 in row 2 (was [-10, -20, 0, 0, 0, 0, -20, -10]).
    # Every other "flat" row in this table uses 0/-10, so that looked like
    # a typo rather than an intentional asymmetry.
    bishop_table = [
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10,    0,   0,   0,   0,   0,    0, -10],
        [-10,   0,  10,  10,  10,  10,   0, -10],
        [-10,  10,  10,  20,  20,  10,  10, -10],
        [-10,  10,  10,  20,  20,  10,  10, -10],
        [-10,   0,  10,  10,  10,  10,   0, -10],
        [-10,    0,   0,   0,   0,   0,    0, -10],
        [-20, -10, -10, -10, -10, -10, -10, -20]
    ]

    rook_table = [
        [0,  0,  0,  0,  0,  0,  0,  0],
        [5, 10, 10, 10, 10, 10, 10,  5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [-5, 0, 0, 0, 0, 0, 0, -5],
        [5, 10,10 ,10 ,10 ,10 ,10 ,5]
    ]

    # NEW: queens previously had no positional table at all. Mild
    # preference for the center, mild penalty for sitting in a corner.
    queen_table = [
        [-20, -10, -10, -5, -5, -10, -10, -20],
        [-10,   0,   0,  0,  0,   0,   0, -10],
        [-10,   0,   5,  5,  5,   5,   0, -10],
        [-5,    0,   5,  5,  5,   5,   0,  -5],
        [0,     0,   5,  5,  5,   5,   0,  -5],
        [-10,   5,   5,  5,  5,   5,   0, -10],
        [-10,   0,   5,  0,  0,   0,   0, -10],
        [-20, -10, -10, -5, -5, -10, -10, -20]
    ]

    # NEW: king wants shelter behind pawns in the middlegame...
    king_table_middlegame = [
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-30, -40, -40, -50, -50, -40, -40, -30],
        [-20, -30, -30, -40, -40, -30, -30, -20],
        [-10, -20, -20, -20, -20, -20, -20, -10],
        [20,   20,   0,   0,   0,   0,  20,  20],
        [20,   30,  10,   0,   0,  10,  30,  20]
    ]

    # ...but wants to centralize and support pawns in the endgame.
    king_table_endgame = [
        [-50, -40, -30, -20, -20, -30, -40, -50],
        [-30, -20, -10,   0,   0, -10, -20, -30],
        [-30, -10,  20,  30,  30,  20, -10, -30],
        [-30, -10,  30,  40,  40,  30, -10, -30],
        [-30, -10,  30,  40,  40,  30, -10, -30],
        [-30, -10,  20,  30,  30,  20, -10, -30],
        [-30, -30,   0,   0,   0,   0, -30, -30],
        [-50, -30, -30, -30, -30, -30, -30, -50]
    ]

    non_king_piece_types = (
        chess.PAWN,
        chess.KNIGHT,
        chess.BISHOP,
        chess.ROOK,
        chess.QUEEN,
    )
    starting_non_king_material = (
        16 * piece_values[chess.PAWN]
        + 4 * piece_values[chess.KNIGHT]
        + 4 * piece_values[chess.BISHOP]
        + 4 * piece_values[chess.ROOK]
        + 2 * piece_values[chess.QUEEN]
    )
    current_non_king_material = 0
    for piece_type in non_king_piece_types:
        current_non_king_material += (
            len(board.pieces(piece_type, chess.WHITE))
            + len(board.pieces(piece_type, chess.BLACK))
        ) * piece_values[piece_type]

    # Bonus or penalty for king protection
    white_board = board.copy(stack=False)
    white_board.turn = chess.WHITE
    white_king_square = white_board.king(chess.WHITE)
    white_king_non_capture_squares = 0
    if white_king_square is not None:
        white_king_non_capture_squares = sum(
            1
            for move in white_board.legal_moves
            if move.from_square == white_king_square
            and not white_board.is_capture(move)
            and not white_board.is_castling(move)
        )

    black_board = board.copy(stack=False)
    black_board.turn = chess.BLACK
    black_king_square = black_board.king(chess.BLACK)
    black_king_non_capture_squares = 0
    if black_king_square is not None:
        black_king_non_capture_squares = sum(
            1
            for move in black_board.legal_moves
            if move.from_square == black_king_square
            and not black_board.is_capture(move)
            and not black_board.is_castling(move)
        )
    # As pieces come off the board, piece-square tables matter less.
    pst_weight = current_non_king_material / starting_non_king_material
    pst_weight = max(0.0, min(1.0, pst_weight))

    for piece_type in piece_values:
        score += len(board.pieces(piece_type, chess.WHITE)) * piece_values[piece_type]
        score -= len(board.pieces(piece_type, chess.BLACK)) * piece_values[piece_type]

    pst_score = 0

    # Add pawn positional bonuses
    for square in board.pieces(chess.PAWN, chess.WHITE):
        row = square // 8
        col = square % 8
        pst_score += pawn_table[row][col]
    
    for square in board.pieces(chess.PAWN, chess.BLACK):
        row = square // 8
        col = square % 8
        pst_score -= pawn_table[7 - row][col]  # Flip for black's perspective

    # Doubled/isolated pawn penalties
    white_pawn_files = [0] * 8
    black_pawn_files = [0] * 8
    for square in board.pieces(chess.PAWN, chess.WHITE):
        white_pawn_files[square % 8] += 1
    for square in board.pieces(chess.PAWN, chess.BLACK):
        black_pawn_files[square % 8] += 1

    for f in range(8):
        # Doubled pawns: penalty for each extra pawn beyond the first on a file
        if white_pawn_files[f] > 1:
            pst_score -= (white_pawn_files[f] - 1) * 5
        if black_pawn_files[f] > 1:
            pst_score += (black_pawn_files[f] - 1) * 5

        # Isolated pawns: no friendly pawns on either adjacent file
        white_neighbors = (white_pawn_files[f - 1] if f > 0 else 0) + (white_pawn_files[f + 1] if f < 7 else 0)
        if white_pawn_files[f] > 0 and white_neighbors == 0:
            pst_score -= 5 * white_pawn_files[f]

        black_neighbors = (black_pawn_files[f - 1] if f > 0 else 0) + (black_pawn_files[f + 1] if f < 7 else 0)
        if black_pawn_files[f] > 0 and black_neighbors == 0:
            pst_score += 5 * black_pawn_files[f]

    # NEW: Passed pawn bonus. A pawn is passed if no enemy pawn occupies
    # its file or either adjacent file on any rank between it and
    # promotion - nothing can ever stop or capture it by advancing
    # straight ahead or diagonally.
    #
    # Kept deliberately small relative to piece_values (pawn=10, queen=90):
    # even a pawn one step from promoting is only a *chance* at a queen,
    # not a guaranteed one, so the bonus tops out well under a rook. A
    # previous version of this used bonuses up to ~100-200, which is more
    # than a queen - that made the engine willing to sacrifice real
    # material to chase or protect "passed" pawns that weren't actually
    # that valuable yet, and cost a lot of the engine's tested strength.
    #
    # Also checks whether the square directly ahead is occupied by any
    # piece (blockaded) - a passed pawn that's physically stuck in front
    # of a piece is worth much less than one that's actually running, even
    # though "passed" (no pawn can ever capture/block it) is still true.
    passed_pawn_bonus_by_rank = [0, 1, 2, 4, 7, 12, 20, 0]  # index = rank, 0 = rank 1

    for square in board.pieces(chess.PAWN, chess.WHITE):
        file = square % 8
        rank = square // 8
        blocking_files = [f for f in (file - 1, file, file + 1) if 0 <= f <= 7]
        is_passed = True
        for enemy_square in board.pieces(chess.PAWN, chess.BLACK):
            enemy_file = enemy_square % 8
            enemy_rank = enemy_square // 8
            if enemy_file in blocking_files and enemy_rank > rank:
                is_passed = False
                break
        if is_passed:
            bonus = passed_pawn_bonus_by_rank[rank] * (1 + (1 - pst_weight) * 0.5)
            square_ahead = square + 8
            if square_ahead <= chess.H8 and board.piece_at(square_ahead) is not None:
                bonus *= 0.5  # blocked - still passed, just not going anywhere yet
            score += bonus

    for square in board.pieces(chess.PAWN, chess.BLACK):
        file = square % 8
        rank = square // 8
        blocking_files = [f for f in (file - 1, file, file + 1) if 0 <= f <= 7]
        is_passed = True
        for enemy_square in board.pieces(chess.PAWN, chess.WHITE):
            enemy_file = enemy_square % 8
            enemy_rank = enemy_square // 8
            if enemy_file in blocking_files and enemy_rank < rank:
                is_passed = False
                break
        if is_passed:
            bonus = passed_pawn_bonus_by_rank[7 - rank] * (1 + (1 - pst_weight) * 0.5)
            square_ahead = square - 8
            if square_ahead >= chess.A1 and board.piece_at(square_ahead) is not None:
                bonus *= 0.5
            score -= bonus

    # Connected/supported passed pawns bonus.
    # "Connected": two passed pawns on adjacent files within one rank of each
    # other - capturing one lets the other run, so together they're much
    # harder to stop than either alone.
    # "Supported": a friendly pawn defends the passed pawn from behind
    # (diagonally) - it can't just be captured for free.
    # Kept small relative to piece_values (pawn=10) since this is a structural
    # plus on top of the passed-pawn bonus already scored elsewhere, not a
    # replacement for it.

    # Detect passed pawns
    white_passed_pawns = []
    for square in board.pieces(chess.PAWN, chess.WHITE):
        file = square % 8
        rank = square // 8
        blocking_files = [f for f in (file - 1, file, file + 1) if 0 <= f <= 7]
        is_passed = True
        for enemy_square in board.pieces(chess.PAWN, chess.BLACK):
            enemy_file = enemy_square % 8
            enemy_rank = enemy_square // 8
            if enemy_file in blocking_files and enemy_rank > rank:
                is_passed = False
                break
        if is_passed:
            white_passed_pawns.append(square)

    # Checks for connected passed pawns
    for square in white_passed_pawns:
        file = square % 8
        rank = square // 8

        # Connected: another white passed pawn on an adjacent file, within one rank
        for other_square in white_passed_pawns:
            if other_square == square:
                continue
            other_file = other_square % 8
            other_rank = other_square // 8
            if abs(other_file - file) == 1 and abs(other_rank - rank) <= 1:
                score += 10
                break

        # Checks for supported passed pawns
        defender_rank = rank - 1
        if defender_rank >= 0:
            for defender_file in (file - 1, file + 1):
                if 0 <= defender_file <= 7:
                    defender_square = defender_rank * 8 + defender_file
                    if board.piece_at(defender_square) == chess.Piece(chess.PAWN, chess.WHITE):
                        score += 8
                        break

    # Bishop pair bonus: two bishops covering both color complexes is a real
    # structural advantage a single bishop or bishop+knight pair doesn't have.
    # Scaled modestly against piece_values (bishop=30) - it's a genuine plus,
    # not worth more than a fraction of a minor piece on its own.
    BISHOP_PAIR_BONUS = 15

    if len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2:
        score += BISHOP_PAIR_BONUS

    if len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2:
        score -= BISHOP_PAIR_BONUS

    # Add piece-square table bonuses for each piece type, scaled by the pst_weight
    # Add knight positional bonus
    for square in board.pieces(chess.KNIGHT, chess.WHITE):
        row = square // 8
        col = square % 8
        pst_score += knight_table[row][col]

    for square in board.pieces(chess.KNIGHT, chess.BLACK):
        row = square // 8
        col = square % 8
        pst_score -= knight_table[7 - row][col]  # Flip for black's perspective

    # Add bishop positional bonus
    for square in board.pieces(chess.BISHOP, chess.WHITE):
        row = square // 8
        col = square % 8
        pst_score += bishop_table[row][col]

    for square in board.pieces(chess.BISHOP, chess.BLACK):
        row = square // 8
        col = square % 8
        pst_score -= bishop_table[7 - row][col]  # Flip for black's perspective

    # Add rook positional bonus
    for square in board.pieces(chess.ROOK, chess.WHITE):
        row = square // 8
        col = square % 8
        pst_score += rook_table[row][col]

    for square in board.pieces(chess.ROOK, chess.BLACK):
        row = square // 8
        col = square % 8
        pst_score -= rook_table[7 - row][col]  # Flip for black's perspective

    # NEW: Add queen positional bonus
    for square in board.pieces(chess.QUEEN, chess.WHITE):
        row = square // 8
        col = square % 8
        pst_score += queen_table[row][col]

    for square in board.pieces(chess.QUEEN, chess.BLACK):
        row = square // 8
        col = square % 8
        pst_score -= queen_table[7 - row][col]  # Flip for black's perspective

    # NEW: Add king positional bonus, blending middlegame/endgame tables
    # by the same pst_weight already used to fade out the other tables.
    for square in board.pieces(chess.KING, chess.WHITE):
        row = square // 8
        col = square % 8
        king_score = (
            king_table_middlegame[row][col] * pst_weight
            + king_table_endgame[row][col] * (1 - pst_weight)
        )
        pst_score += king_score

    for square in board.pieces(chess.KING, chess.BLACK):
        row = square // 8
        col = square % 8
        king_score = (
            king_table_middlegame[7 - row][col] * pst_weight
            + king_table_endgame[7 - row][col] * (1 - pst_weight)
        )
        pst_score -= king_score

    # King mobility penalty/bonus (weighted like PST):
    # black king mobility is a black penalty (+score), white king mobility is a white penalty (-score)
    # Bonus for white when black king mobility is more
    score += black_king_non_capture_squares

    # Bonus for black when white king mobility is more
    score -= white_king_non_capture_squares

    score += pst_score * pst_weight

    # Add attack bonus for BLACK attacking WHITE
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        # check if it's a black piece
        if piece is not None and piece.color == chess.BLACK:

            attacks = board.attacks(square)

            for target_square in attacks:
                target_piece = board.piece_at(target_square)
                # check if it's a white piece
                if target_piece is not None and target_piece.color == chess.WHITE:
                    value = piece_values[target_piece.piece_type]
                    score -= value/7
    
    # Add attack bonus for WHITE attacking BLACK
    for square in chess.SQUARES:
        piece = board.piece_at(square)

        # check if it's a white piece
        if piece is not None and piece.color == chess.WHITE:

            attacks = board.attacks(square)

            for target_square in attacks:
                target_piece = board.piece_at(target_square)
                # check if it's a black piece
                if target_piece is not None and target_piece.color == chess.BLACK:
                    value = piece_values[target_piece.piece_type]
                    score += value/7

    
    # Add defense bonus for BLACK
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        # check if it's a black piece
        if piece is not None and piece.color == chess.BLACK:

            attacks = board.attacks(square)

            for target_square in attacks:
                target_piece = board.piece_at(target_square)
                # check if it's a white piece
                if target_piece is not None and target_piece.color == chess.BLACK:
                    value = piece_values[target_piece.piece_type]
                    score -= value/7
    
    # Add defense bonus for WHITE
    for square in chess.SQUARES:
        piece = board.piece_at(square)

        # check if it's a white piece
        if piece is not None and piece.color == chess.WHITE:

            attacks = board.attacks(square)

            for target_square in attacks:
                target_piece = board.piece_at(target_square)
                # check if it's a black piece
                if target_piece is not None and target_piece.color == chess.WHITE:
                    value = piece_values[target_piece.piece_type]
                    score += value/7

    if board.is_check():
        if board.turn == chess.WHITE:
            score -= 10  # Black is giving check, good for Black
        else:
            score += 10  # White is giving check, good for White

    # Fifty-move-rule awareness: right now the engine only "notices" a
    # 50-move draw at the exact node where can_claim_draw() flips true,
    # which is a sudden cliff (advantage -> flat 0) rather than something
    # search can see coming. With no signal beforehand, a won position
    # gives the engine no reason to prefer a progress-making move
    # (capture / pawn push, which resets board.halfmove_clock) over an
    # aimless one, so it can shuffle right up to the cliff and then get
    # surprised by it. Tapering the score down as the clock climbs gives
    # search a gradient toward progress well before that point, since a
    # move that resets the clock will score higher than one that doesn't,
    # all else equal.
    clock_progress = board.halfmove_clock / 100.0
    fifty_move_decay = max(0.0, 1.0 - clock_progress ** 2)
    score *= fifty_move_decay

    return score
