import requests
import chess

SYZYGY_API_URL = "https://tablebase.lichess.ovh/standard"
USE_SYZYGY = False
TIMEOUT = 5

syzygy_failed = False

def syzygy_error():
    global syzygy_failed
    if not syzygy_failed:
        print("Syzygy API not responding, switching to evaluation")
        syzygy_failed = True


def get_piece_count(board):
    """Count the total number of pieces on the board"""
    return bin(board.occupied).count('1')


def get_syzygy_move(board):
    global syzygy_failed

    if not USE_SYZYGY:
        return None

    piece_count = get_piece_count(board)
    
    if piece_count > 7:
        return None
    
    if not syzygy_failed:
        print("Pieces Below 7, activate syzygy API")
        
    try:
        fen = board.fen()
        params = {"fen": fen}
        
        response = requests.get(SYZYGY_API_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        syzygy_failed = False
        
        if not data or "moves" not in data or not data["moves"]:
            syzygy_error()
            return None
        
        moves = data["moves"]
        
        for move in moves[:]:
            if move.get("zeroing", False):
                moves.remove(move)
        
        if not moves:
            syzygy_error()
            return None
        
        best = moves[0]
        
        san = best.get("san")
        if not san:
            syzygy_error()
            return None
        
        try:
            move = board.parse_san(san)
            category = best.get("category", "unknown")
            dtz = best.get("dtz", "N/A")
            print(f"Syzygy found best move: {move} (Category: {category}, DTZ: {dtz})")
            return move
        except Exception:
            syzygy_error()
            return None
    
    except requests.exceptions.Timeout:
        syzygy_error()
        return None
    except requests.exceptions.ConnectionError:
        syzygy_error()
        return None
    except requests.exceptions.RequestException:
        syzygy_error()
        return None
    except Exception:
        syzygy_error()
        return None