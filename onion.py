#!/usr/bin/env python3
"""
onion.py
Client-side script to build the onion structure from routes.json.
"""
import json, os, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROUTE_FILE = "/tmp/onion_mininet/routes.json"
OUTFILE = "/tmp/onion_mininet/onion.out"

def encrypt_layer(key_hex, inner_bytes):
    """Encrypts the inner payload (as bytes) with AES-GCM, returning the outer JSON-encoded bytes."""
    key = bytes.fromhex(key_hex)
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aes.encrypt(nonce, inner_bytes, None)

    # Returns the structure the router expects: {"nonce": "...", "payload": "..."}
    return json.dumps({
        "nonce": base64.b64encode(nonce).decode(),
        "payload": base64.b64encode(ciphertext).decode()
    }).encode() 

def main():
    if not os.path.exists(ROUTE_FILE):
        print(f"Error: Route file not found at {ROUTE_FILE}")
        return

    route_info = json.load(open(ROUTE_FILE))
    route_hops = route_info["route"] # [r1, r2, r3]
    server_info = route_info["server"]

    # 1. Innermost Layer (L3 - for r3)
    # This structure tells the EXIT node (r3) to deliver the data.
    inner_most_layer_data = {
        "server": server_info,
        "data": "HELLO_FROM_CLIENT_VIA_ONION" 
    }
    onion_blob = json.dumps(inner_most_layer_data).encode()

    # 2. Encrypt the remaining layers (r3 -> r2 -> r1)
    # The loop iterates backward, from the last hop (r3, index 2) back to the first hop (r1, index 0).
    for i in range(len(route_hops) - 1, -1, -1):
        router_key = route_hops[i]["key"]
        
        # If this is the final hop (r3), we just encrypt the raw message.
        if i == len(route_hops) - 1:
            onion_blob = encrypt_layer(router_key, onion_blob)
            continue
        
        # For all intermediate hops (r2 and r1), the inner payload must contain the forwarding instruction
        # for the *next* router (i+1). This ensures r1 gets the next hop info for r2.
        next_hop = route_hops[i + 1] 
        
        outer_layer_data = {
            "next": {
                "ip": next_hop["ip"],
                "port": next_hop["port"]
            },
            "payload": base64.b64encode(onion_blob).decode()
        }
        
        # Encrypt the forwarding instruction using the key of the current router (r_i)
        onion_blob = encrypt_layer(
            router_key,
            json.dumps(outer_layer_data).encode()
        )

    open(OUTFILE, "wb").write(onion_blob)
    print(f"Onion built and saved at {OUTFILE}")

if __name__ == "__main__":
    main()
