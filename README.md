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

3) In the Mininet CLI: build and send
```bash
h1 python3 /tmp/onion_mininet/onion.py --route /tmp/onion_mininet/routes.json --outfile /tmp/onion_mininet/onion.out --message "HELLO"
h1 python3 /tmp/onion_mininet/client.py --route /tmp/onion_mininet/routes.json --onion /tmp/onion_mininet/onion.out
```

4) When done: `exit` the CLI. Network tears down automatically. Logs are in `/tmp/onion_mininet/*.log`.

## No xterms?
```bash
sudo python3 net.py
```
Then run captures from the Mininet CLI (e.g., `r1 tcpdump -n -i r1-eth1 udp`) before sending with the same two commands above.
