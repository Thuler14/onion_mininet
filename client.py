#!/usr/bin/env python3
"""
client.py
Client-side script to send the onion blob to the first hop.
"""
import json, socket, time, argparse, os

NETDIR = "/tmp/onion_mininet"
OUTFILE = f"{NETDIR}/onion.out"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--route", required=True)
    args = parser.parse_args()

    if not os.path.exists(args.route) or not os.path.exists(OUTFILE):
        print(f"[CLIENT] Error: Routes file ({args.route}) or Onion Blob ({OUTFILE}) not found. Did you run onion.py?")
        return

    routes = json.load(open(args.route))
    first_hop = routes["route"][0]

    blob = open(OUTFILE, "rb").read()

    print(f"[CLIENT] Connecting to first hop: {first_hop['ip']}:{first_hop['port']}")
    try:
        t0 = time.time()
        s = socket.create_connection((first_hop["ip"], first_hop["port"]))
        s.sendall(blob)
        s.shutdown(socket.SHUT_WR)

        reply = s.recv(4096)
        t1 = time.time()

        print(f"[CLIENT] elapsed {t1 - t0:.4f}s")
        print("[CLIENT] Server reply:", reply.decode(errors="replace"))
        s.close()
    except Exception as e:
        print(f"[CLIENT] Connection/Transmission Error: {e}")

if __name__ == "__main__":
    main()
