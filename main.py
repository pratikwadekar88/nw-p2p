# main.py

import time
from simulation import Simulation
from config import NUM_PEERS

if __name__ == '__main__':
    start_time = time.time()

    sim = Simulation()
    sim.setup()
    sim.run()
    # sim.collect_results()
    sim.compare_peer_blockchains()

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Simulation completed in {elapsed_time:.2f} seconds.")

    # Visualize the network topology
    sim.visualize_network_topology()

    # Visualize the blockchain of all peers
    for peer_id in range(NUM_PEERS):
        peer_id = str(peer_id)
        sim.visualize_blockchain(peer_id)
