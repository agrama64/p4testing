if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <num_layers> <total_duration>"
  exit 1
fi

num_layers=$1
total_duration=$2

# Calculate num_routers as 2^num_layers - 1
num_routers=$(( 2**$num_layers - 1 ))

rm -r ${num_layers}_layer_tree_tcp
rm -r ${num_layers}_layer_tree_topo

python gen_tree.py ${num_layers}

echo "Running with num_routers=$num_routers and total_duration=$total_duration"

./move.sh
make clean
make run
sudo PATH=/home/p4/p4dev-python-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python python3 ../../utils/traffic.py -t ${num_layers}_layer_tree_topo/topology.json -j build/basic.json -b simple_switch_grpc -n ${num_routers} -d ${total_duration}
cp -r pcaps "${num_layers}_layer_tree_tcp/"
mkdir ${num_layers}_layer_tree_tcp_logs
cp -r logs "${num_layers}_layer_tree_tcp_logs/"