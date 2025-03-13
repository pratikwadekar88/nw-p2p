import time
from simulation import Simulation
from config import NUM_PEERS
from visualize import Visualizer

if __name__ == '__main__':
    start_time = time.time()

    sim = Simulation()
    sim.setup()
    sim.run(1.0)

    visual = Visualizer(sim.peers)
    # Compare peer blockchains
    visual.compare_peer_blockchains()

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Simulation completed in {elapsed_time:.2f} seconds.")

    # Visualize the network topology
    visual.visualize_network_topology()

    # Visualize the blockchain of all peers
    for peer_id in range(NUM_PEERS):
        visual.visualize_blockchain(str(peer_id))
