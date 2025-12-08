"""Simple echo server used as the onion exit destination."""
import argparse
import socket
import threading
import traceback
from pathlib import Path
from typing import Iterable, Tuple


def handle(conn: socket.socket, addr: Tuple[str, int], logpath: Path) -> None:
    try:
        data = conn.recv(4096)
        if not data:
            return
        msg = data.decode(errors="replace")
        with logpath.open("a") as f:
            f.write(f"[SERVER] got from {addr}: {msg}\n")
        conn.sendall(b"OK")
    except Exception:
        with logpath.open("a") as f:
            f.write("[SERVER] exception:\n")
            f.write(traceback.format_exc())
    finally:
        try:
            conn.close()
        except Exception:
            pass


def start_server(port: int, logpath: Path) -> None:
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(8)

    with logpath.open("a") as f:
        f.write(f"[SERVER] listening on 0.0.0.0:{port}\n")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn, addr, logpath), daemon=True).start()


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the destination server.")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    start_server(args.port, Path(args.log))


if __name__ == "__main__":
    main()
