"""Paths and defaults shared across the Mininet onion demo."""
from pathlib import Path

NETDIR = Path("/tmp/onion_mininet")
ROUTE_FILE = NETDIR / "routes.json"
ONION_OUT = NETDIR / "onion.out"
DEFAULT_MESSAGE = "HELLO_FROM_CLIENT_VIA_ONION"

# Files we copy into each Mininet host so they can run locally.
SCRIPT_FILES = (
    "node.py",
    "server.py",
    "client.py",
    "onion.py",
    "paths.py",
)

REPO_ROOT = Path(__file__).resolve().parent


def ensure_netdir() -> None:
    """Create NETDIR if missing."""
    NETDIR.mkdir(parents=True, exist_ok=True)
