make clean
make run
./correct.sh
sudo PATH=/home/p4/p4dev-python-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 ../../utils/traffic.py -t complex-topo/topology.json -j build/basic.json -j build/load_balancer.json -j build/switch.json -b simple_switch_grpc

