"""Build an onion-encoded payload based on a routes.json description."""
import argparse
import base64
import json
import os
from pathlib import Path
from typing import Iterable, Mapping, Union

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from paths import DEFAULT_MESSAGE, ONION_OUT, ROUTE_FILE, ensure_netdir

RouteHop = Mapping[str, Union[str, int]]


def encrypt_layer(key_hex: str, inner_bytes: bytes) -> bytes:
    """Encrypt the inner payload with AES-GCM using the provided hex key."""
    key = bytes.fromhex(key_hex)
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aes.encrypt(nonce, inner_bytes, None)

    return json.dumps(
        {
            "nonce": base64.b64encode(nonce).decode(),
            "payload": base64.b64encode(ciphertext).decode(),
        }
    ).encode()


def build_layers(route_hops: Iterable[RouteHop], server_info: Mapping[str, Union[str, int]], payload: str) -> bytes:
    """Create the onion blob by wrapping from the last hop to the first."""
    onion_blob = json.dumps({"server": server_info, "data": payload}).encode()

    hops = list(route_hops)
    for i in range(len(hops) - 1, -1, -1):
        router_key = str(hops[i]["key"])

        if i == len(hops) - 1:
            onion_blob = encrypt_layer(router_key, onion_blob)
            continue

        next_hop = hops[i + 1]
        outer_layer = {
            "next": {"ip": next_hop["ip"], "port": next_hop["port"]},
            "payload": base64.b64encode(onion_blob).decode(),
        }
        onion_blob = encrypt_layer(router_key, json.dumps(outer_layer).encode())

    return onion_blob


def build_onion(route_path: Path = ROUTE_FILE, outfile: Path = ONION_OUT, message: str = DEFAULT_MESSAGE) -> Path:
    """Build the onion blob and persist it to disk."""
    route_path = Path(route_path)
    outfile = Path(outfile)

    if not route_path.exists():
        raise FileNotFoundError(f"Route file not found: {route_path}")

    ensure_netdir()

    route_info = json.loads(route_path.read_text())
    route_hops = route_info["route"]
    server_info = route_info["server"]

    onion_blob = build_layers(route_hops, server_info, payload=message)
    outfile.write_bytes(onion_blob)
    return outfile


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build the onion payload from a route file.")
    parser.add_argument("--route", default=str(ROUTE_FILE), help="Path to routes.json")
    parser.add_argument("--outfile", default=str(ONION_OUT), help="Where to write the onion blob")
    parser.add_argument("--message", default=DEFAULT_MESSAGE, help="Payload to deliver to the destination server")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        outfile = build_onion(Path(args.route), Path(args.outfile), args.message)
        print(f"Onion built and saved at {outfile}")
    except Exception as exc:
        print(f"[ONION] Error: {exc}")


if __name__ == "__main__":
    main()
