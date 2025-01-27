from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController
from random import randint
import time

controller_ip = '127.0.0.1'
controller_port = 6653

net = Mininet(controller=RemoteController)
net.addController('c0', controller=RemoteController, ip=controller_ip, port=controller_port)


print(net.hosts)

h1 = net.get('h1')
h2 = net.get('h2')

for _ in range(5):
    bandwidth = f"{randint(1, 10)}M"
    duration = randint(5, 15)
    print(f"Generating {bandwidth} ftraffic for {duration}s")
    h1.cmd('iperf -s -u &')
    h2.cmd(f'iperf -c {h1.IP()} -u -b {bandwidth} -t {duration}')
    time.sleep(randint(2, 5))

#CLI(net)