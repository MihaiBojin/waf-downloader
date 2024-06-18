import sys
from waf_logs import compute_time


def main() -> None:
    """Functional test that ensures the library can be imported and utilized"""

    _ = compute_time(at=None, delta_by_minutes=-1)
    print("OK.", file=sys.stderr)


if __name__ == "__main__":
    main()
