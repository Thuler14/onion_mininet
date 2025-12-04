#!/usr/bin/env python3
import argparse, socket, threading, traceback

def handle(conn, addr, log):
# ... (existing implementation is fine) ...
    try:
        data = conn.recv(4096)
        if not data:
            return
        msg = data.decode(errors="replace")

        with open(log, "a") as f:
            f.write(f"[SERVER] got from {addr}: {msg}\n")

        conn.sendall(b"OK")
    except Exception:
        with open(log, "a") as f:
            f.write("[SERVER] exception:\n")
            f.write(traceback.format_exc())
    finally:
        try: conn.close()
        except: pass

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--log", required=True)
    args = p.parse_args()

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", args.port))
    s.listen(8)

    with open(args.log, "a") as f:
        f.write(f"[SERVER] listening on 0.0.0.0:{args.port}\n")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle, args=(conn, addr, args.log), daemon=True).start()

if __name__ == "__main__":
    main()
