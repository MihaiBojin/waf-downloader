from datetime import timedelta, datetime, timezone
from importlib import resources
from pathlib import Path
from typing import List, Optional


def compute_time(at: Optional[datetime], delta_by_minutes: int = 0) -> datetime:
    """Computes a time represented by the current minute, rounded down to 0 seconds.
    If 'at' is None, the function will use the current time as basis for the computation.
    'delta_by_minutes' allows for adding or subtracting minutes from the computed time.
    """

    if at is None:
        at = datetime.now(tz=timezone.utc)

    # Further round down to :xx:00
    target = at.replace(second=0, microsecond=0)

    # Add the desired minute interval
    # If delta_by_minutes is negative, this will add a negative interval, i.e., point the time to the past
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
