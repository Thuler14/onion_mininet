# Onion Mininet Demo

Fast steps to run and capture.

## Prereqs
- Linux + Mininet (run with sudo)
- Python 3
- Wireshark or tcpdump (optional for captures)

## Run
1) Start everything (opens xterms so you can launch Wireshark/tcpdump):
```bash
sudo python3 net.py --xterms
```
You’ll land in the Mininet CLI. No traffic has been sent yet.

2) In any xterm (e.g., r1): start capture (traffic is TCP, default ports 9001-9003 for routers and 9009 for server)
```bash
wireshark &
# or watch all TCP on a link
tcpdump -n -i r1-eth1 tcp
# or narrow to the server port
tcpdump -n -i h2-eth0 tcp port 9009
```

3) In the Mininet CLI: build and send (single step, defaults used; onion is saved to runtime/onion.out each run)
```bash
h1 python3 client.py --message "HELLO"    # build+send with custom payload
h1 python3 client.py                      # build+send with default payload
h1 python3 client.py --reuse              # reuse existing onion.out instead of rebuilding
```

Defaults: `client.py` and `onion.py` look for `runtime/routes.json` and write/read `runtime/onion.out`. You can override with `--route`/`--onion-file` if you want different paths. By default the onion is rebuilt each run; use `--reuse` to resend an existing blob.

If you prefer the two-step flow (defaults still apply):
```bash
h1 python3 onion.py --message "HELLO"
h1 python3 client.py --onion-file runtime/onion.out
```

4) When done: `exit` the CLI. Network tears down automatically. Logs are in `runtime/*.log` under the repo.

## No xterms?
```bash
sudo python3 net.py
```
Then run captures from the Mininet CLI (e.g., `r1 tcpdump -n -i r1-eth1 tcp`) before sending with the same two commands above.
