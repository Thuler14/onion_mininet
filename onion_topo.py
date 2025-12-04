#!/usr/bin/env python3
"""
onion_topo.py
Creates a linear topology: h1 <-> r1 <-> r2 <-> r3 <-> h2
"""
import os, json, secrets, time
from mininet.net import Mininet
from mininet.node import OVSSwitch
from mininet.link import TCLink
from mininet.log import setLogLevel, info
from mininet.cli import CLI

NETDIR = '/tmp/onion_mininet'

def write_file_on_host(host, path, content):
    host.cmd('mkdir -p ' + os.path.dirname(path))
    host.cmd("python3 - <<'PY'\nopen('%s','w').write(%r)\nPY" % (path, content))

def generate_keyhex():
    return secrets.token_hex(32)

def run():
    setLogLevel('info')
    
    # Clean up previous state
    os.system(f"rm -rf {NETDIR}; mkdir -p {NETDIR}")

    net = Mininet(switch=OVSSwitch, link=TCLink)
    net.addController('c0')
    h1 = net.addHost('h1'); r1 = net.addHost('r1')
    r2 = net.addHost('r2'); r3 = net.addHost('r3')
    h2 = net.addHost('h2')

    net.addLink(h1, r1); net.addLink(r1, r2)
    net.addLink(r2, r3); net.addLink(r3, h2)

    net.start()

    # IP Configuration
    h1.cmd("ifconfig h1-eth0 10.0.1.10/24 up")
    r1.cmd("ifconfig r1-eth0 10.0.1.1/24 up"); r1.cmd("ifconfig r1-eth1 10.0.2.1/24 up")
    r2.cmd("ifconfig r2-eth0 10.0.2.2/24 up"); r2.cmd("ifconfig r2-eth1 10.0.3.2/24 up")
    r3.cmd("ifconfig r3-eth0 10.0.3.1/24 up"); r3.cmd("ifconfig r3-eth1 10.0.4.1/24 up")
    h2.cmd("ifconfig h2-eth0 10.0.4.10/24 up")

    for r in (r1, r2, r3):
        r.cmd("sysctl -w net.ipv4.ip_forward=1")

    h1.cmd("ip route add default via 10.0.1.1")
    h2.cmd("ip route add default via 10.0.4.1")

    # Static routes
    r1.cmd("ip route add 10.0.3.0/24 via 10.0.2.2")
    r1.cmd("ip route add 10.0.4.0/24 via 10.0.2.2")
    r2.cmd("ip route add 10.0.1.0/24 via 10.0.2.1")
    r2.cmd("ip route add 10.0.4.0/24 via 10.0.3.1")
    r3.cmd("ip route add 10.0.1.0/24 via 10.0.3.2")
    r3.cmd("ip route add 10.0.2.0/24 via 10.0.3.2")

    # Key and Route Generation
    k1 = generate_keyhex(); k2 = generate_keyhex(); k3 = generate_keyhex()
    route_obj = {
        "route": [
            {"ip": "10.0.1.1", "port": 9001, "key": k1},
            {"ip": "10.0.2.2", "port": 9002, "key": k2},
            {"ip": "10.0.3.1", "port": 9003, "key": k3}
        ],
        "server": {"ip": "10.0.4.10", "port": 9009}
    }

    write_file_on_host(r1, f"{NETDIR}/r1.key", k1)
    write_file_on_host(r2, f"{NETDIR}/r2.key", k2)
    write_file_on_host(r3, f"{NETDIR}/r3.key", k3)
    write_file_on_host(h1, f"{NETDIR}/routes.json", json.dumps(route_obj))

    # Copy scripts
    cwd = os.getcwd()
    scripts = ['router.py', 'server.py', 'client.py', 'onion.py']
    for host in (r1, r2, r3, h2, h1):
        host.cmd(f"mkdir -p {NETDIR}")
        for s in scripts:
            script_path = os.path.join(cwd, s)
            if os.path.exists(script_path):
                host.cmd(f"cp {script_path} {NETDIR}/{s}")

    info('\n*** Environment Setup Complete ***\n')
    info('*** Start services from Mininet CLI: (h2, r3, r2, r1) then (h1 onion.py, h1 client.py) ***\n')

    CLI(net)
    net.stop()

if __name__ == '__main__':
    run()
