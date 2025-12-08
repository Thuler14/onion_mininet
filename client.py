"""Client helper that pushes the onion blob to the first hop."""
import argparse
import json
import socket
import time
from pathlib import Path
from typing import Iterable, Tuple

from onion import build_onion_bytes
from settings import DEFAULT_MESSAGE, ONION_OUT, ROUTE_FILE


def send_onion(
    route_path: Path = ROUTE_FILE,
    onion_path: Path = ONION_OUT,
    onion_bytes: bytes | None = None,
) -> Tuple[float, str]:
    route_path = Path(route_path)
    onion_path = Path(onion_path)

    if onion_bytes is None:
        if not route_path.exists() or not onion_path.exists():
            raise FileNotFoundError(
                f"Missing route file ({route_path}) or onion blob ({onion_path}). Run onion builder first."
            )
        blob = onion_path.read_bytes()
    else:
        blob = onion_bytes

    routes = json.loads(route_path.read_text())
    first_hop = routes["route"][0]

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
    parser.add_argument(
        "--onion-file",
        default=str(ONION_OUT),
        help="Path to onion blob (created each run unless --reuse is given)",
    )
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Reuse an existing onion blob from --onion-file instead of rebuilding",
    )
    parser.add_argument(
        "--message",
        help="Plaintext to wrap and send (builds onion in memory). If omitted and no onion file exists, a default message is used.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        route_path = Path(args.route)
        onion_path = Path(args.onion_file)

        if args.message:
            blob = build_onion_bytes(route_path, args.message)
            onion_path.write_bytes(blob)
            elapsed, reply = send_onion(route_path, onion_bytes=blob)
        elif args.reuse and onion_path.exists():
            elapsed, reply = send_onion(route_path, onion_path)
        else:
            blob = build_onion_bytes(route_path, DEFAULT_MESSAGE)
            onion_path.write_bytes(blob)
            elapsed, reply = send_onion(route_path, onion_bytes=blob)
        print(f"[CLIENT] elapsed {elapsed:.4f}s")
        print(f"[CLIENT] Server reply: {reply}")
    except Exception as exc:
        print(f"[CLIENT] Connection/Transmission Error: {exc}")


if __name__ == "__main__":
    main()
