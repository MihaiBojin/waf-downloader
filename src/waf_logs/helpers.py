from datetime import timedelta, datetime, timezone
from importlib import resources
from pathlib import Path
from typing import List, Optional


def compute_time(at: Optional[datetime], delta_by_minutes: int = 0) -> datetime:
    """Computes a time before the previous minute divisible by 5, by the specified duration.
    If 'at' is None, compute the most recent timestamp (i.e., :00, :05, :10, etc.)
    """

    if at is None:
        at = datetime.now(tz=timezone.utc)

    # Round down to the previous minute, divisible by 5 (i.e, if time is currently :07:xx minutes, round down to :05:xx minutes)
    target = at - timedelta(minutes=at.minute % 5)

    # Further round down to :xx:00
    target = target.replace(second=0, microsecond=0)

    # Substract the desired minute interval
    target += timedelta(minutes=delta_by_minutes)

    return target


def iso_to_datetime(at: str) -> datetime:
    """Converts and ISO string date to a datetime obj."""
    return datetime.fromisoformat(at)


def validate_name(name: str):
    """Raise an error if the name contains characters other than a-zA-Z0-9_-"""
    for c in name.lower():
        if not "a" <= c <= "z" and not "0" <= c <= "9" and c != "_" and c != "-":
            raise ValueError(f"Invalid query name: {name}")


def read_text(file_path: str) -> str:
    """Read all lines from file"""

    with open(file_path, "r") as file:
        lines = file.readlines()
        return "".join(lines)


def read_file(from_path: str, package_name: Optional[str] = None) -> str:
    """Reads words from a file that is either on disk or part of the specified package."""

    # If a package, retrieve path first
    data_path = from_path
    if package_name is not None:
        data_path = str(resources.files(package_name).joinpath(from_path))

    return read_text(data_path)


def list_files(from_path: str, package_name: Optional[str] = None) -> List[str]:
    """Reads all files at the specified path that is either on disk or part of the specified package"""

    # If a package, retrieve path first
    if package_name is not None:
        data_path = resources.files(package_name) / from_path
        return sorted([entry.name for entry in data_path.iterdir() if entry.is_file()])

    return sorted(
        [entry.name for entry in Path(from_path).iterdir() if entry.is_file()]
    )
