"""Router service for peeling and forwarding onion layers."""
import argparse
import base64
import json
import socket
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass
class RouterConfig:
    port: int
    key_hex: str
    logpath: Path


def recv_all(conn: socket.socket, timeout: float = 2.0) -> bytes:
    data = b""
    conn.settimeout(timeout)
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
    except Exception:
        pass
    return data


def proxy_stream(upstream: socket.socket, downstream: socket.socket) -> None:
    # Bidirectional copy to keep the connection open until both sides finish.
    def copy(src: socket.socket, dst: socket.socket) -> None:
        try:
            while True:
                chunk = src.recv(4096)
                if not chunk:
                    break
                dst.sendall(chunk)
        except Exception:
            pass
        try:
            dst.shutdown(socket.SHUT_WR)
        except Exception:
            pass

    t1 = threading.Thread(target=copy, args=(upstream, downstream), daemon=True)
    t2 = threading.Thread(target=copy, args=(downstream, upstream), daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def decrypt_layer(key_hex: str, payload: bytes) -> dict:
    top = json.loads(payload.decode())
    nonce = base64.b64decode(top["nonce"])
    ciphertext = base64.b64decode(top["payload"])
    aes = AESGCM(bytes.fromhex(key_hex))
    inner_bytes = aes.decrypt(nonce, ciphertext, None)
    return json.loads(inner_bytes.decode())


def handle_client(conn: socket.socket, addr: Tuple[str, int], cfg: RouterConfig) -> None:
    try:
        raw = recv_all(conn)
        if not raw:
            conn.close()
            return

        inner = decrypt_layer(cfg.key_hex, raw)
        with cfg.logpath.open("a") as lf:
            lf.write(f"[ROUTER] Decrypted layer from {addr}: next={inner.get('next')}, server={inner.get('server')}\n")

        if "next" in inner:
            next_hop = inner["next"]
            dst_ip = next_hop["ip"]
            dst_port = int(next_hop["port"])
            next_blob = base64.b64decode(inner["payload"])

            s = socket.create_connection((dst_ip, dst_port), timeout=5)
            s.sendall(next_blob)
            s.shutdown(socket.SHUT_WR)

            with cfg.logpath.open("a") as lf:
                lf.write(f"[ROUTER] Forwarded to next router {dst_ip}:{dst_port}\n")

            proxy_stream(conn, s)
            return

        server_info = inner.get("server")
        final_data = inner.get("data")

        if server_info:
            dst_ip = server_info["ip"]
            dst_port = int(server_info["port"])
            s = socket.create_connection((dst_ip, dst_port), timeout=5)

            if isinstance(final_data, (dict, list)):
                data_to_send = json.dumps(final_data)
            elif isinstance(final_data, str):
                data_to_send = final_data
            else:
                data_to_send = str(final_data)

            s.sendall(data_to_send.encode())
            s.shutdown(socket.SHUT_WR)

            with cfg.logpath.open("a") as lf:
                lf.write(f"[ROUTER] Delivered to final server {dst_ip}:{dst_port}\n")

            proxy_stream(conn, s)
            return

        with cfg.logpath.open("a") as lf:
            lf.write("[ROUTER] Layer contained neither 'next' nor 'server' — dropping.\n")

    except Exception:
        with cfg.logpath.open("a") as lf:
            lf.write("[ROUTER] exception:\n")
            lf.write(traceback.format_exc())
    finally:
        try:
            conn.close()
        except Exception:
            pass


def start_router(port: int, keyfile: Path, logpath: Path) -> None:
    cfg = RouterConfig(port=port, key_hex=Path(keyfile).read_text().strip(), logpath=Path(logpath))

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", cfg.port))
    sock.listen(8)

    with cfg.logpath.open("a") as lf:
        lf.write(f"[ROUTER] listening on 0.0.0.0:{cfg.port}\n")

    while True:
        conn, addr = sock.accept()
        threading.Thread(target=handle_client, args=(conn, addr, cfg), daemon=True).start()


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run an onion router node.")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--keyfile", required=True)
    parser.add_argument("--log", required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)

    start_router(args.port, Path(args.keyfile), Path(args.log))


if __name__ == "__main__":
    main()
