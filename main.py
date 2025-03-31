# main.py
import time
from simulation import Simulation
from visualize import Visualizer
from config import NUM_PEERS

if __name__ == '__main__':
    start_time = time.time()

    sim = Simulation()
    sim.setup()
    sim.run()

    visual = Visualizer(sim.peers)
    visual.compare_peer_blockchains()
    for peer_id in range(NUM_PEERS):
        visual.visualize_blockchain(str(peer_id))
    visual.visualize_network_topology()

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Simulation completed in {elapsed_time:.2f} seconds.")
