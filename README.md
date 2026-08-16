<div align="center">
<img src="assets/logo.png" width="200" height="200">

# Aurelius

A free, open source, Python-based chess engine with advanced search algorithms, sophisticated position evaluation, and opening book support.

Version `0.2.1`
ELO `~1450`
NPS `~2000`

</div>

## Features

### Core Engine
- **UCI-Compatible Chess**: Built on the `python-chess` library for full legal move validation and chess rule support
- **Minimax Search with Alpha-Beta Pruning**: Efficient game tree exploration with alpha-beta pruning for optimal move selection
- **Iterative Deepening**: Searches depth 1, then 2, then 3, and so on, using each shallow iteration's best move to improve move ordering for the next - stopping once a time budget runs out or a maximum depth is reached. Falls back to a plain fixed-depth search when no time budget is given (adjustable via the `DEPTH` constant in `search.py`, default 4 plies)

> Note: Aurelius is a command line program. You may want to use it in your own chess GUI.
> It is confirmed that CuteChess is compatible.

### Advanced Search Optimizations
- **Transposition Tables (TT)**: Caches evaluated positions to avoid redundant calculations
  - Stores depth, score, flags (exact/lower/upper bounds), and best moves
  - Automatic cache clearing at 200,000 entries to manage memory
  - Significant performance boost through TT hits tracking, and carries over between iterative deepening's depths so deeper iterations benefit from shallower ones' work

- **Null Move Pruning**: Identifies positions where opponent cannot improve, enabling aggressive pruning
  - Adaptive reduction depth (1-2 plies based on search depth)
  - Skipped in check positions and when only pawns remain
  - Configurable via `use_null` parameter

- **Late Move Reduction (LMR)**: Reduces search depth for quiet moves that appear less promising
  - Applies to moves after index 3 in quiet positions
  - Can be re-searched at full depth if score exceeds alpha
  - Accelerates search by ~3-4x for quiet move sequences

- **Killer Moves**: Tracks moves that caused cutoffs at each depth level
  - Prioritizes killer moves in sibling branches for better move ordering
  - Exploits common tactical patterns across similar positions

- **Pondering**: Uses idle time between moves to think ahead
  - After playing a move, guesses the opponent's most likely reply and searches that position immediately, storing results in the shared transposition table
  - If the guess is right, the next real search starts with cached analysis already in place instead of starting cold
  - `play.py`: pondering runs synchronously in the gap before prompting for your move (configurable via `PONDER_ENABLED`/`PONDER_TIME_SECONDS`)
  - `uci.py`: full UCI ponder protocol support (`go ponder` / `ponderhit` / `stop`) via a background thread, so the engine stays responsive to GUI commands while pondering - only one search ever runs at a time, the thread just keeps stdin from blocking


### Move Ordering
- **Root Moves**: Prioritized by promotions (800+ bonus), captures (1000 + MVV-LVA), and checks (150 bonus)
- **Inner Moves**: Tactical moves (captures/promotions) evaluated before quiet moves
- **Transposition Move Priority**: Best moves from TT evaluated first for faster cutoffs
- **Killer Move Integration**: Quiet moves that caused cutoffs prioritized in similar positions

### Position Evaluation
- **Material Count**: Standard piece values (Pawn: 10, Knight/Bishop: 30, Rook: 50, Queen: 90)
- **Piece-Square Tables (PST)**: Position-dependent bonuses/penalties for optimal piece placement
  - Dynamic weighting based on remaining material (matters less in endgames)
  - Tables for pawns, knights, bishops, rooks, queens, and king (king table blends a middlegame "stay sheltered" table with an endgame "centralize" table based on remaining material)
  - King mobility scoring (encourages safe king positioning)
- **Pawn Structure**:
  - Doubled and isolated pawn penalties
  - Passed pawn bonus, scaled by how close the pawn is to promotion and weighted more heavily as material comes off the board
  - Connected passed pawn bonus (two passed pawns on adjacent files supporting each other's advance)
  - Supported passed pawn bonus (a friendly pawn defending the passed pawn from behind)
- **Bishop Pair Bonus**: Rewards holding both bishops, since together they cover every square on the board regardless of where they stand
- **Attack/Defense Scoring**: Evaluates attacking and defending capabilities
  - Black attacks on White pieces reduce score by 1/7 of the attacked piece's value
  - White attacks on Black pieces increase score by 1/7 of the attacked piece's value
  - Similar defense bonuses for protecting own pieces
- **Special Cases**:
  - Draw and checkmate detection run first, before any of the above - if the game is already decided, the rest of the evaluation is skipped entirely rather than computed and discarded
  - Immediate detection of checkmate (±10,000,000) and drawn positions (stalemate, insufficient material, threefold repetition, fifty-move rule)

### Opening Book
- **JSON-Based Opening Library** (`openings/openings.json`): Pre-loaded chess openings with multiple lines per opening
- **Intelligent Book Selection**: 
  - Selects openings matching current position history
  - Randomly chooses between candidate opening lines (seeded for reproducibility)
- **Graceful Fallback**: Automatically switches to search when:
  - Opening line is deviated from
  - Opening line is completed
  - No matching opening is found
- **Line Validation**: Ensures all stored lines are legal and playable before loading
- **Statistics Tracking**: Reports total loaded lines from opening book

### Endgame Tablebases (Syzygy)
- **Syzygy Integration**: Queries tablebase data for perfect endgame play
  - Activated for positions with 7 or fewer pieces
  - Provides best moves via Syzygy tablebase lookups
- **Graceful Fallback**: Automatically switches to regular evaluation if:
  - Tablebase lookup is unavailable or fails
  - Position has more than 7 pieces
  - Lookup returns no valid moves
- **Performance**: Fast, accurate endgame play through proven tablebase knowledge

### Interactive Gameplay
- **Human vs Engine**: Play as White or Black against the engine
- **Flexible Move Input**: 
  - Accepts standard algebraic notation (SAN)
  - Handles castling formats: `0-0`, `0-0-0`, `O-O`, `O-O-O`
  - Tolerates common typos and formatting variations
- **Real-time Statistics**: Displays evaluation time and engine thinking process
- **Game Analysis**: Verbose mode shows every evaluated move and their scores, including a per-depth breakdown when iterative deepening is active

## Small Implementation Details

- **Version**: 0.2.1
- **Default Engine Color**: White
- **Default Search Depth Cap**: 4 plies for fixed-depth mode (via the `DEPTH` constant); when iterative deepening is active (default in `play.py`), the depth cap is set high (99) and a 5-second time budget is what actually limits the search
- **Transposition Table Size**: 200,000 entries maximum
- **Null Move Settings**: Minimum depth 3, reduction of 1-2 plies
- **LMR Settings**: Minimum depth 3, applies to moves after index 3
- **Syzygy Settings**: Activated for positions with 7 or fewer pieces
- **Verbose Logging**: Optional detailed move analysis and statistics, including per-depth iterative deepening output
- **Error Handling**: Graceful handling of illegal moves with informative error messages
- **Performance Metrics**: Tracks nodes evaluated, TT cache hits, null move cutoffs, and LMR reductions per search

## Architecture

```
main.py          - Entry point and game loop
play.py          - Interactive chess gameplay interface
search.py        - Minimax search with alpha-beta pruning, iterative deepening, and optimizations
eval.py          - Position evaluation function with piece-square tables and pawn structure heuristics
opening_book.py  - Opening book management and move selection
syzygy.py        - Endgame tablebase queries
openings/        - Opening book JSON data
__init__.py      - Package initialization
```

## Dependencies

- `python-chess`: For board representation, move generation, and rule validation

## Running the Engine

```bash
python main.py
```

This starts an interactive game where you play against Aurelius as the opponent.

## Benchmark

- Estimated ~600ELO on Chess.com against Komodo 6 at 1000ELO (0.1.1)
- Estimated ~900ELO on chessigma.com against Stockfish 18 at max (0.2.0)
- Estimated **~1450ELO** on chessigma.com against Stockfish 18 at max (0.2.1)
> Chess.com is not used anymore because the rating estimator requires both players to have an official established rating attached to the game (e.g., in imported PGNs). If the ratings are missing or set to zero, the estimator will return zero/nothing.
