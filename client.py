"""Client helper that pushes the onion blob to the first hop."""
import argparse
import json
import socket
import time
from pathlib import Path
from typing import Iterable, Tuple

from paths import ONION_OUT, ROUTE_FILE


def send_onion(route_path: Path = ROUTE_FILE, onion_path: Path = ONION_OUT) -> Tuple[float, str]:
    route_path = Path(route_path)
    onion_path = Path(onion_path)

    if not route_path.exists() or not onion_path.exists():
        raise FileNotFoundError(
            f"Missing route file ({route_path}) or onion blob ({onion_path}). Run onion builder first."
        )

    routes = json.loads(route_path.read_text())
    first_hop = routes["route"][0]
    blob = onion_path.read_bytes()

    start = time.time()
    with socket.create_connection((first_hop["ip"], int(first_hop["port"])), timeout=5) as sock:
        sock.sendall(blob)
        sock.shutdown(socket.SHUT_WR)
        reply = sock.recv(4096)
    elapsed = time.time() - start
    return elapsed, reply.decode(errors="replace")


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Send the onion blob to the first hop.")
    parser.add_argument("--route", default=str(ROUTE_FILE), help="Path to routes.json")
    parser.add_argument("--onion", default=str(ONION_OUT), help="Path to onion blob produced by onion.py")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        elapsed, reply = send_onion(Path(args.route), Path(args.onion))
        print(f"[CLIENT] elapsed {elapsed:.4f}s")
        print(f"[CLIENT] Server reply: {reply}")
    except Exception as exc:
        print(f"[CLIENT] Connection/Transmission Error: {exc}")


if __name__ == "__main__":
    main()
