import runpy
from pathlib import Path


def main():
    play_path = Path(__file__).with_name("play.py")
    runpy.run_path(str(play_path), run_name="__main__")


if __name__ == "__main__":
    main()
