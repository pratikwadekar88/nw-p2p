# main.py

import time
from simulation import Simulation

if __name__ == '__main__':
    start_time = time.time()

    sim = Simulation()
    sim.setup()
    sim.run()
    sim.collect_results()
    sim.compare_peer_blockchains()

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Simulation completed in {elapsed_time:.2f} seconds.")

    # Visualize the network topology
    sim.visualize_network_topology()

    # Visualize the blockchain of a specific peer
    peer_id = '0'  # Ensure peer_id is a string
    sim.visualize_blockchain(peer_id)
