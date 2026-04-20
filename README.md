<div align="center">
<img src="assets/logo.png" width="200" height="200">

# Aurelius

A free, open source, Python-based chess engine with advanced search algorithms, sophisticated position evaluation, and opening book support.

Version `0.1.0`

</div>

## Features

### Core Engine
- **UCI-Compatible Chess**: Built on the `python-chess` library for full legal move validation and chess rule support
- **Minimax Search with Alpha-Beta Pruning**: Efficient game tree exploration with alpha-beta pruning for optimal move selection
- **Configurable Search Depth**: Default depth of 5 plies (adjustable via `DEPTH` constant in `search.py`)

### Advanced Search Optimizations
- **Transposition Tables (TT)**: Caches evaluated positions to avoid redundant calculations
  - Stores depth, score, flags (exact/lower/upper bounds), and best moves
  - Automatic cache clearing at 200,000 entries to manage memory
  - Significant performance boost through TT hits tracking

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

### Move Ordering
- **Root Moves**: Prioritized by promotions (800+ bonus), captures (1000 + MVV-LVA), and checks (150 bonus)
- **Inner Moves**: Tactical moves (captures/promotions) evaluated before quiet moves
- **Transposition Move Priority**: Best moves from TT evaluated first for faster cutoffs
- **Killer Move Integration**: Quiet moves that caused cutoffs prioritized in similar positions

### Position Evaluation
- **Material Count**: Standard piece values (Pawn: 10, Knight/Bishop: 30, Rook: 50, Queen: 90)
- **Piece-Square Tables (PST)**: Position-dependent bonuses/penalties for optimal piece placement
  - Dynamic weighting based on remaining material (matters less in endgames)
  - Separate tables for pawns, knights, bishops, and rooks
  - King mobility scoring (encourages safe king positioning)
- **Attack/Defense Scoring**: Evaluates attacking and defending capabilities
  - Black attacks on White pieces reduce score by 1/5 of piece value
  - White attacks on Black pieces increase score by 1/5 of piece value
  - Similar defense bonuses for protecting own pieces
- **Special Cases**: Immediate detection of checkmate (±10,000,000) and drawn positions

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

### Interactive Gameplay
- **Human vs Engine**: Play as White or Black against the engine
- **Flexible Move Input**: 
  - Accepts standard algebraic notation (SAN)
  - Handles castling formats: `0-0`, `0-0-0`, `O-O`, `O-O-O`
  - Tolerates common typos and formatting variations
- **Real-time Statistics**: Displays evaluation time and engine thinking process
- **Game Analysis**: Verbose mode shows every evaluated move and their scores

## Small Implementation Details

- **Version**: 0.1.0
- **Default Engine Color**: White
- **Transposition Table Size**: 200,000 entries maximum
- **Null Move Settings**: Minimum depth 3, reduction of 1-2 plies
- **LMR Settings**: Minimum depth 3, applies to moves after index 3
- **Verbose Logging**: Optional detailed move analysis and statistics
- **Error Handling**: Graceful handling of illegal moves with informative error messages
- **Performance Metrics**: Tracks nodes evaluated, TT cache hits, null move cutoffs, and LMR reductions per search

## Architecture

```
main.py          - Entry point and game loop
play.py          - Interactive chess gameplay interface
search.py        - Minimax search with alpha-beta pruning, optimizations
eval.py          - Position evaluation function with piece-square tables
opening_book.py  - Opening book management and move selection
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

- Estimated ~600ELO on Chess.com against Komodo 6 at 1000ELO
- 