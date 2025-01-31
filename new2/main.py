# main.py

from simulation import Simulation

if __name__ == '__main__':
    sim = Simulation()
    sim.setup()
    sim.run()
    sim.collect_results()
    # Optional: sim.visualize_blockchain(peer_id)
