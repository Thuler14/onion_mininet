#!/usr/bin/env python3
"""
router.py
Router script for Mininet. Decrypts one layer and forwards the payload or delivers to the server.
"""
import argparse, socket, json, base64, threading, traceback
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def recv_all(conn, timeout=2.0):
    data = b''
    conn.settimeout(timeout)
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk: break
            data += chunk
    except Exception:
        pass
    return data

def proxy_stream(a, b):
    def copy(src, dst):
        try:
            while True:
                chunk = src.recv(4096)
                if not chunk: break
                dst.sendall(chunk)
        except Exception:
            pass
        try: dst.shutdown(socket.SHUT_WR)
        except Exception: pass
    t1 = threading.Thread(target=copy, args=(a,b), daemon=True)
    t2 = threading.Thread(target=copy, args=(b,a), daemon=True)
    t1.start(); t2.start()
    t1.join(); t2.join()

def handle_client(conn, addr, key_hex, logpath):
    try:
        raw = recv_all(conn)
        if not raw:
            conn.close()
            return

        # 1. Decrypt outer layer
        key = bytes.fromhex(key_hex)
        top = json.loads(raw.decode())
        nonce = base64.b64decode(top["nonce"])
        ciphertext = base64.b64decode(top["payload"])
        
        aes = AESGCM(key)
        inner_bytes = aes.decrypt(nonce, ciphertext, None)
        inner = json.loads(inner_bytes.decode())
        
        with open(logpath, 'a') as lf:
            lf.write(f"[ROUTER] Decrypted layer from {addr}: next={inner.get('next')}, server={inner.get('server')}\n")

        # 2. Case 1: Intermediate Router (forward to next hop)
        if "next" in inner:
            next_hop = inner["next"]
            next_blob_b64 = inner["payload"]
            
            dst_ip = next_hop["ip"]
            dst_port = int(next_hop["port"])

            s = socket.create_connection((dst_ip, dst_port), timeout=5)
            
            next_blob = base64.b64decode(next_blob_b64) 
            s.sendall(next_blob)
            s.shutdown(socket.SHUT_WR) # FIX: Stabilize socket connection

            with open(logpath, 'a') as lf:
                lf.write(f"[ROUTER] Forwarded to next router {dst_ip}:{dst_port}\n")

            proxy_stream(conn, s)
            return

        # 3. Case 2: Exit Router (send to end server)
        server_info = inner.get("server")
        final_data = inner.get("data")
        
        if server_info:
            dst_ip = server_info["ip"]
            dst_port = int(server_info["port"])
            s = socket.create_connection((dst_ip, dst_port), timeout=5)

            data_to_send = ""
            if isinstance(final_data, (dict, list)):
                data_to_send = json.dumps(final_data)
            elif isinstance(final_data, str):
                data_to_send = final_data
            else:
                data_to_send = str(final_data)
            
            s.sendall(data_to_send.encode())
            s.shutdown(socket.SHUT_WR) # FIX: Stabilize socket connection for server

            with open(logpath, 'a') as lf:
                lf.write(f"[ROUTER] Delivered to final server {dst_ip}:{dst_port}\n")

            proxy_stream(conn, s)
            return

        # 4. Error case
        with open(logpath, 'a') as lf:
            lf.write("[ROUTER] Layer contained neither 'next' nor 'server' — dropping.\n")

    except Exception:
        with open(logpath, 'a') as lf:
            lf.write("[ROUTER] exception:\n")
            lf.write(traceback.format_exc())
    finally:
        try: conn.close()
        except: pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--keyfile', required=True)
    parser.add_argument('--log', required=True)
    args = parser.parse_args()

    key_hex = open(args.keyfile).read().strip()

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", args.port))
    sock.listen(8)
    
    with open(args.log, 'a') as lf:
        lf.write(f"[ROUTER] listening on 0.0.0.0:{args.port}\n")

    while True:
        conn, addr = sock.accept()
        threading.Thread(
            target=handle_client,
            args=(conn, addr, key_hex, args.log),
            daemon=True
        ).start()

if __name__ == "__main__":
    main()
