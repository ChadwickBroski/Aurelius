import chess

def evaluate(board):

    score = 0
    
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

    bishop_table = [
        [-20, -10, -10, -10, -10, -10, -10, -20],
        [-10,   -20,   0,   0,   0,   0,   -20, -10],
        [-10,   0,  10,  10,  10,  10,   0, -10],
        [-10,  10,  10,  20,  20,  10,  10, -10],
        [-10,  10,  10,  20,  20,  10,  10, -10],
        [-10,   0,  10,  10,  10,  10,   0, -10],
        [-10,   20,   0,   0,   0,   0,   20, -10],
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

    if board.is_checkmate():
        if board.turn == chess.WHITE:
            return -10000000  # Black wins
        return 10000000  # White wins
    
    if board.is_stalemate() or board.is_insufficient_material() or board.is_seventyfive_moves() or board.is_fivefold_repetition() or board.can_claim_draw() or board.can_claim_threefold_repetition() or board.can_claim_fifty_moves() or board.is_repetition(3) or board.is_fifty_moves() or board.is_variant_draw():
        return 0 # Draw

    return score
