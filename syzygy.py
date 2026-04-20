import requests
import chess

SYZYGY_API_URL = "https://tablebase.lichess.ovh/standard"
TIMEOUT = 5


def get_piece_count(board):
    """Count the total number of pieces on the board"""
    return bin(board.occupied).count('1')


def get_syzygy_move(board):
    """
    Query Lichess syzygy tablebase API and return the best move.
    Returns the best move as a chess.Move object or None.
    """
    piece_count = get_piece_count(board)
    
    # Only query syzygy for endgames with 7 or fewer pieces
    if piece_count > 7:
        return None
    
    print(f"Pieces Below 7, activate syzygy API")
    
    try:
        fen = board.fen()
        params = {"fen": fen}
        
        response = requests.get(SYZYGY_API_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if there are moves available
        if not data or "moves" not in data or not data["moves"]:
            print("Syzygy API not responding, switching to evaluation")
            return None
        
        moves = data["moves"]
        
        # Remove moves where zeroing is True
        for move in moves[:]:  # Iterate over a copy to safely remove items
            if move.get("zeroing", False):
                moves.remove(move)
        
        if not moves:
            print("Syzygy API not responding, switching to evaluation")
            return None
        
        # Get the best move (first move in the filtered list)
        best = moves[0]
        
        # Convert SAN notation to chess move
        san = best.get("san")
        if not san:
            print("Syzygy API not responding, switching to evaluation")
            return None
        
        try:
            move = board.parse_san(san)
            category = best.get("category", "unknown")
            dtz = best.get("dtz", "N/A")
            print(f"Syzygy found best move: {move} (Category: {category}, DTZ: {dtz})")
            return move
        except Exception as e:
            print("Syzygy API not responding, switching to evaluation")
            return None
    
    except requests.exceptions.Timeout:
        print("Syzygy API not responding, switching to evaluation")
        return None
    except requests.exceptions.ConnectionError:
        print("Syzygy API not responding, switching to evaluation")
        return None
    except requests.exceptions.RequestException as e:
        print("Syzygy API not responding, switching to evaluation")
        return None
    except Exception as e:
        print("Syzygy API not responding, switching to evaluation")
        return None
