# Onion Mininet Demo

Tiny onion-routing lab built on Mininet: `h1` wraps a payload in three AES-GCM layers, hops through `r1 -> r2 -> r3`, and lands on `h2` where a simple server echoes back. Keys and routes are generated fresh each run and written to `runtime/`.

## Requirements
- Linux with sudo (Mininet needs root). Tested on Ubuntu 22.04 LTS and Linux Mint.
- Mininet + `xterm` (for optional terminals); `sudo apt install mininet xterm`
- Python 3.10+; `python3 -m pip install --user cryptography`
- Optional: Wireshark or tcpdump for packet capture

## Quickstart (recommended)
```bash
git clone https://github.com/Thuler14/onion_mininet.git
cd onion_mininet
# If you downloaded a ZIP instead of cloning:
# unzip onion_mininet.zip && cd onion_mininet

# Start the topology (add --xterms if you want capture terminals)
sudo python3 net.py
# or, to open xterms on r1,r2,r3,h2,h1 for Wireshark/tcpdump
sudo python3 net.py --xterms
```

You land in the Mininet CLI; services are already running and `runtime/routes.json` plus router keys are in place. In any xterm (e.g., `r1`), start a capture if you want:
```bash
wireshark &
# or
tcpdump -n -i r1-eth1 tcp
tcpdump -n -i h2-eth0 tcp port 9009
```

From the Mininet CLI, send traffic (onion is rebuilt each time unless you reuse):
```bash
h1 python3 client.py --message "HELLO"    # build + send custom payload
h1 python3 client.py                      # build + send default payload
h1 python3 client.py --reuse              # resend existing runtime/onion.out
```

Two-step build + send if you prefer:
```bash
h1 python3 onion.py --message "HELLO"
h1 python3 client.py --onion-file runtime/onion.out
```

Quit with `exit`; Mininet tears down. Logs and artifacts live in `runtime/` (router logs, server log, `routes.json`, `onion.out`).

## Headless mode
Skip xterms and run everything inside the CLI:
```bash
sudo python3 net.py
```
Start captures from the CLI (e.g., `r1 tcpdump -n -i r1-eth1 tcp`) before sending with the same `h1 python3 ...` commands above.

## What’s happening under the hood
- `net.py` builds a 3-hop topology, generates per-run AES keys, writes `runtime/routes.json`, and launches router/server processes.
- `onion.py` wraps the message in layered AES-GCM, producing `runtime/onion.out`.
- `client.py` sends the blob to the first hop and prints the echoed reply + timing.
- `node.py` peels/forwards layers; `server.py` echoes and logs the final payload.
