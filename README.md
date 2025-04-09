# Generating Traffic with P4

## Generic Ring Topology Generation

If you don't care about how everything works, just run ./run_ring.sh ${num_routers} ${total_duration}

This will generate all the topology and device files necessary for a ring topology with ${num_routers} routers and the total simulation time will be ${total_duration}. These files are contained in ${num_routers}_ring_topo.

It will then run that topology through mininet with every possible host pairing: (num_routers * (num_routers - 1)) total and ensure that the total sim time adds up to ${total_duration}. The topo file and pcaps can both be found in the ${num_routers}_ring_tcp directory. This directory can then be copied into the invinf examples folder and run through invinf tool (./run.sh ${num_routers}_ring_tcp)


gen_topo.py creates all of the files for generating mininet traffic.
traffic.py enumerates pairs of hosts to send packets to one another based on num_routers and total_duration (this functionality can be found in generate_traffic())
run_ring.sh is a shell script that gets the pcaps


