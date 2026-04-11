import json
import random
import chess


class OpeningBook:
    def __init__(self, path, enabled=True, seed=None):
        self.path = path
        self.enabled = enabled
        self._rng = random.Random(seed)

        self._openings = []
        self._chosen = None
        self._engine_color = None
        self._active = enabled

        self._load_book()

    @property
    def loaded_lines(self):
        return sum(len(entry["lines"]) for entry in self._openings)

    @property
    def active(self):
        return self._active

    def _load_book(self):
        if not self.enabled:
            self._active = False
            return

        try:
            with open(self.path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception:
            self._active = False
            return

        openings = data.get("openings", []) if isinstance(data, dict) else []
        cleaned = []

        for opening in openings:
            if not isinstance(opening, dict):
                continue

            name = opening.get("name")
            lines = opening.get("lines", [])
            if not isinstance(name, str) or not isinstance(lines, list):
                continue

            valid_lines = []
            for line in lines:
                if self._is_valid_line(line):
                    valid_lines.append(line)

            if valid_lines:
                cleaned.append({"name": name, "lines": valid_lines})

        self._openings = cleaned
        if not self._openings:
            self._active = False

    @staticmethod
    def _is_valid_line(line):
        if not isinstance(line, list) or not line:
            return False

        board = chess.Board()
        for san in line:
            if not isinstance(san, str):
                return False
            try:
                move = board.parse_san(san)
            except ValueError:
                return False
            board.push(move)

        return True

    def _choose_opening(self, board):
        if not self._openings:
            self._active = False
            return

        candidates = []
        for opening in self._openings:
            for line in opening["lines"]:
                if self._history_matches_line(board, line) and len(board.move_stack) < len(line):
                    candidates.append({"name": opening["name"], "line": line})

        if not candidates:
            self._active = False
            return

        self._chosen = self._rng.choice(candidates)

    @staticmethod
    def _history_matches_line(board, line):
        if len(board.move_stack) > len(line):
            return False

        replay = chess.Board()
        for ply_index, actual_move in enumerate(board.move_stack):
            try:
                expected_move = replay.parse_san(line[ply_index])
            except ValueError:
                return False

            if expected_move != actual_move:
                return False

            replay.push(expected_move)

        return True

    def next_move(self, board, engine_color):
        """
        Returns (move, opening_name, san, status)
        status can be: "book", "deviated", "line_complete", "inactive", "no_move"
        """
        if not self._active:
            return None, None, None, "inactive"

        if self._engine_color is None:
            self._engine_color = engine_color

        if board.turn != self._engine_color:
            return None, None, None, "no_move"

        if self._chosen is None:
            self._choose_opening(board)
            if self._chosen is None:
                return None, None, None, "inactive"

        name = self._chosen["name"]
        line = self._chosen["line"]

        if not self._history_matches_line(board, line):
            previous_name = name
            self._chosen = None
            self._choose_opening(board)
            if self._chosen is None:
                return None, previous_name, None, "deviated"
            name = self._chosen["name"]
            line = self._chosen["line"]

        ply = len(board.move_stack)
        if ply >= len(line):
            completed_name = name
            self._chosen = None
            self._choose_opening(board)
            if self._chosen is None:
                return None, completed_name, None, "line_complete"
            name = self._chosen["name"]
            line = self._chosen["line"]
            ply = len(board.move_stack)

        replay = chess.Board()
        for i in range(ply):
            replay.push(replay.parse_san(line[i]))

        san = line[ply]
        try:
            move = replay.parse_san(san)
        except ValueError:
            self._active = False
            return None, name, None, "inactive"

        if move not in board.legal_moves:
            self._active = False
            return None, name, None, "inactive"

        return move, name, san, "book"
