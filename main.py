import time
from simulation import Simulation
from config import NUM_PEERS, TIMEOUT
from visualize import Visualizer
from visualize_overlay import Visualizer as OverlayVisualizer

if __name__ == '__main__':
    start_time = time.time()

    sim = Simulation()
    sim.setup()
    sim.run(TIMEOUT)

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Simulation completed in {elapsed_time:.2f} seconds.")

    visual = Visualizer(sim.peers)

    malicious_peers = {}
    for peer_id, peer in sim.peers.items():
        malicious_peers[peer_id] = peer

    overlay_visual = OverlayVisualizer(malicious_peers)

    # Compare peer blockchains
    visual.compare_peer_blockchains()

    # Visualize the network topology
    visual.visualize_network_topology()
    overlay_visual.visualize_network_topology()

    # Visualize the blockchain of all peers
    for peer_id in range(NUM_PEERS):
        visual.visualize_blockchain(str(peer_id))
