if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <num_routers> <output_directory>"
  exit 1
fi

num_routers=$1
total_duration=$2

rm -r ${num_routers}_ring_tcp
rm -r ${num_routers}_ring_topo

python gen_topo.py ${num_routers}

echo "Running with num_routers=$num_routers and total_duration=$total_duration"

./move.sh
make clean
make run
sudo PATH=/home/p4/p4dev-python-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 ../../utils/traffic.py -t ${num_routers}_ring_topo/topology.json -j build/basic.json -b simple_switch_grpc -n ${num_routers} -d ${total_duration}
cp -r pcaps "${num_routers}_ring_tcp/"
mkdir ${num_routers}_ring_tcp_logs
cp -r logs "${num_routers}_ring_tcp_logs/"