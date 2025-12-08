#!/usr/bin/env python3
"""One-shot runner: start topology, launch services, build onion, send once."""
import argparse
import json
import os
import secrets

from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.term import makeTerm

from paths import NETDIR, SCRIPT_FILES

ROUTER_PORTS = [9001, 9002, 9003]
SERVER_PORT = 9009


def write_file_on_host(host, path: str, content: str) -> None:
    host.cmd("mkdir -p " + os.path.dirname(path))
    host.cmd("python3 - <<'PY'\nopen('%s','w').write(%r)\nPY" % (path, content))


def generate_route_and_keys() -> tuple[dict, tuple[str, str, str]]:
    k1 = secrets.token_hex(32)
    k2 = secrets.token_hex(32)
    k3 = secrets.token_hex(32)
    route_obj = {
        "route": [
            {"ip": "10.0.1.1", "port": ROUTER_PORTS[0], "key": k1},
            {"ip": "10.0.2.2", "port": ROUTER_PORTS[1], "key": k2},
            {"ip": "10.0.3.1", "port": ROUTER_PORTS[2], "key": k3},
        ],
        "server": {"ip": "10.0.4.10", "port": SERVER_PORT},
    }
    return route_obj, (k1, k2, k3)


def configure_links(net: Mininet) -> None:
    h1, r1, r2, r3, h2 = (net.get(n) for n in ("h1", "r1", "r2", "r3", "h2"))
    h1.cmd("ifconfig h1-eth0 10.0.1.10/24 up")
    r1.cmd("ifconfig r1-eth0 10.0.1.1/24 up"); r1.cmd("ifconfig r1-eth1 10.0.2.1/24 up")
    r2.cmd("ifconfig r2-eth0 10.0.2.2/24 up"); r2.cmd("ifconfig r2-eth1 10.0.3.2/24 up")
    r3.cmd("ifconfig r3-eth0 10.0.3.1/24 up"); r3.cmd("ifconfig r3-eth1 10.0.4.1/24 up")
    h2.cmd("ifconfig h2-eth0 10.0.4.10/24 up")

    for r in (r1, r2, r3):
        r.cmd("sysctl -w net.ipv4.ip_forward=1")

    h1.cmd("ip route add default via 10.0.1.1")
    h2.cmd("ip route add default via 10.0.4.1")

    r1.cmd("ip route add 10.0.3.0/24 via 10.0.2.2")
    r1.cmd("ip route add 10.0.4.0/24 via 10.0.2.2")
    r2.cmd("ip route add 10.0.1.0/24 via 10.0.2.1")
    r2.cmd("ip route add 10.0.4.0/24 via 10.0.3.1")
    r3.cmd("ip route add 10.0.1.0/24 via 10.0.3.2")
    r3.cmd("ip route add 10.0.2.0/24 via 10.0.3.2")


def copy_scripts(hosts, cwd: str) -> None:
    for host in hosts:
        host.cmd(f"mkdir -p {NETDIR}")
        for script in SCRIPT_FILES:
            src = os.path.join(cwd, script)
            if os.path.exists(src):
                host.cmd(f"cp {src} {NETDIR}/{script}")


def start_services(net: Mininet, keys) -> None:
    h1, r1, r2, r3, h2 = (net.get(n) for n in ("h1", "r1", "r2", "r3", "h2"))

    write_file_on_host(r1, f"{NETDIR}/r1.key", keys[0])
    write_file_on_host(r2, f"{NETDIR}/r2.key", keys[1])
    write_file_on_host(r3, f"{NETDIR}/r3.key", keys[2])

    h2.popen(f"python3 {NETDIR}/server.py --port {SERVER_PORT} --log {NETDIR}/server.log")
    r3.popen(f"python3 {NETDIR}/node.py --port {ROUTER_PORTS[2]} --keyfile {NETDIR}/r3.key --log {NETDIR}/r3.log")
    r2.popen(f"python3 {NETDIR}/node.py --port {ROUTER_PORTS[1]} --keyfile {NETDIR}/r2.key --log {NETDIR}/r2.log")
    r1.popen(f"python3 {NETDIR}/node.py --port {ROUTER_PORTS[0]} --keyfile {NETDIR}/r1.key --log {NETDIR}/r1.log")


def open_xterms(net: Mininet, targets) -> None:
    for name in targets:
        node = net.get(name)
        makeTerm(node, term='xterm', title=name)


def run(interactive: bool, open_terms: bool) -> None:
    setLogLevel("info")
    os.system(f"rm -rf {NETDIR}; mkdir -p {NETDIR}")

    net = Mininet(switch=OVSSwitch, link=TCLink)
    net.addController("c0")
    h1 = net.addHost("h1"); r1 = net.addHost("r1")
    r2 = net.addHost("r2"); r3 = net.addHost("r3")
    h2 = net.addHost("h2")

    net.addLink(h1, r1); net.addLink(r1, r2)
    net.addLink(r2, r3); net.addLink(r3, h2)
    net.start()

    configure_links(net)
    route_obj, keys = generate_route_and_keys()

    write_file_on_host(h1, f"{NETDIR}/routes.json", json.dumps(route_obj))
    copy_scripts((r1, r2, r3, h2, h1), os.getcwd())
    start_services(net, keys)

    if open_terms:
        info("\n*** Opening xterms (e.g., start Wireshark/tcpdump on r1).\n")
        open_xterms(net, ("r1", "r2", "r3", "h2", "h1"))

    info("\n*** Ready to capture and send. In the Mininet CLI, run:\n")
    info(f"    h1 python3 {NETDIR}/onion.py --route {NETDIR}/routes.json --outfile {NETDIR}/onion.out --message \"HELLO\"\n")
    info(f"    h1 python3 {NETDIR}/client.py --route {NETDIR}/routes.json --onion {NETDIR}/onion.out\n")
    info("You can start Wireshark/tcpdump in the xterm windows before sending.\n")

    CLI(net)
    net.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full onion demo in one command")
    parser.add_argument("--xterms", action="store_true", help="Open xterms on r1,r2,r3,h2,h1 for captures")
    parser.add_argument("--interactive", action="store_true", help="(kept for compatibility; CLI is always opened)")
    args = parser.parse_args()
    run(interactive=True, open_terms=args.xterms)


if __name__ == "__main__":
    main()
