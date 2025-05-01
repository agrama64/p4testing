if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <num_hosts> <total_duration>"
  exit 1
fi

num_hosts=$1
total_duration=$2

./move.sh
make clean
make run
sudo PATH=/home/p4/p4dev-python-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 ../../utils/traffic.py -t nat-topo/topology.json -j build/basic.json -j build/switch.json -j build/nat.json -b simple_switch_grpc -n ${num_hosts} -d ${total_duration}
