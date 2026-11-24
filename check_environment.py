"""Check this computer for the pipeline starter. Run it with: uv run check_environment.py"""

import importlib.metadata
import socket
import subprocess
import sys


def first_line(*command):
    """The first line a command prints, or None if it cannot run."""
    try:
        done = subprocess.run(command, capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return done.stdout.strip().split("\n")[0] or None


def installed(package):
    """The installed version of a package, or None."""
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def port_is_free(port):
    """True when nothing is listening on the port, so the mock API can start there."""
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) != 0


version = ".".join(str(part) for part in sys.version_info[:3])
named = first_line("git", "config", "user.name") and first_line("git", "config", "user.email")
checks = [
    ("Python 3.11 or newer", version if sys.version_info >= (3, 11) else None, "uv run --python 3.13 check_environment.py"),
    ("Git", first_line("git", "--version"), "install Git, then open a new terminal"),
    ("Git name and email", "set" if named else None, 'git config --global user.name "Your Name" (and user.email)'),
    ("uv", first_line("uv", "--version"), "install uv, then open a new terminal"),
    ("DuckDB", installed("duckdb"), "run: uv sync"),
    ("requests", installed("requests"), "run: uv sync"),
    ("pytest", installed("pytest"), "run: uv sync"),
    ("Port 8000 is free for the mock API", "free" if port_is_free(8000) else None, "stop the program that uses port 8000, or start the API with --port 8001 and set API_URL"),
]
passed = 0
for label, found, fix in checks:
    if found:
        passed += 1
        print(f"PASS  {label}: {found}")
    else:
        print(f"FAIL  {label}\n      Fix: {fix}")
print(f"{passed} of {len(checks)} checks passed.")
sys.exit(0 if passed == len(checks) else 1)
