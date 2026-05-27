import runpy
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent

    if any(arg.lower() in {'uci', '--uci'} for arg in sys.argv[1:]):
        target = root / 'uci.py'
    else:
        target = root / 'play.py'

    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main()
