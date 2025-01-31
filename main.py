# main.py

import time
from simulation import Simulation

if __name__ == '__main__':
    sim = Simulation()
    sim.setup()
    sim.run()
    sim.collect_results()
    sim.compare_peer_blockchains()  # Compare peer blockchains
    end_time = time.time()
    elapsed_time = end_time - sim.current_time
    print(f"Simulation completed in {elapsed_time:.2f} seconds.")

    # Visualize the network topology
    sim.visualize_network_topology()

    # Visualize the blockchain of a specific peer
    peer_id = '0'  # Replace with the peer ID you want to visualize
    sim.visualize_blockchain(1,peer_id)
    sim.visualize_blockchain(2,'1')
    sim.visualize_blockchain(2,'9')
