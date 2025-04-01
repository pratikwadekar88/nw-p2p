# simulation.py
import random, heapq, os, shutil, numpy as np
from peer import Peer
from network import Network
from event import EventType, Event
from block import Block
from config import *

class Simulation:
    def __init__(self):
        """
        Initializes simulation parameters.
        """
        self.peers = {}            # peer_id -> Peer
        self.event_queue = []
        self.current_time = 0
        self.parent_dir = "simOut"
        self.log_file_path = os.path.join(self.parent_dir, 'simulation_log.txt')
        self.log_file = None
        self.log_interval = 50     # seconds

    # def setup(self):
    #     """
    #     Sets up simulation:
    #       - Creates peers and assigns parameters (hash power, malicious flag, etc.).
    #       - Selects one malicious node as the ringmaster.
    #       - Initializes the network (including overlay among malicious nodes).
    #       - Creates and assigns the genesis block.
    #     """
    #     # Remove previous simulation output directory if exists.
    #     if os.path.exists(self.parent_dir):
    #         shutil.rmtree(self.parent_dir)
    #     os.makedirs(self.parent_dir, exist_ok=True)
    #     self.log_file = open(self.log_file_path, 'w')
    #     self.log_file.write("Simulation setup started.\n")

    #     # Create peers
    #     peer_ids = [str(i) for i in range(NUM_PEERS)]
    #     num_malicious = int(PERCENT_MALICIOUS * NUM_PEERS)
    #     malicious_peers = set(random.sample(peer_ids, num_malicious))
    #     for pid in peer_ids:
    #         # Honest nodes: slow & low CPU; malicious nodes: fast & high CPU.
    #         is_malicious = pid in malicious_peers
    #         is_slow = not is_malicious
    #         is_low_cpu = not is_malicious
    #         peer = Peer(pid, is_slow, is_low_cpu, is_malicious=is_malicious)
    #         self.peers[pid] = peer

    #     honest_count = NUM_PEERS - num_malicious
    #     # ATTACKER_FACTOR is defined in config.py; it represents the multiplier for malicious nodes' hash power.
    #     # total_weight = honest_count * 1 + num_malicious * ATTACKER_FACTOR
    #     # for peer in self.peers.values():
    #     #     if peer.is_malicious:
    #     #         peer.hash_power = ATTACKER_FACTOR / total_weight
    #     #     else:
    #     #         peer.hash_power = 1 / total_weight
    #     # Select a random malicious node as the ringmaster
    #     malicious_nodes = [peer for peer in self.peers.values() if peer.is_malicious]
    #     if malicious_nodes:
    #         ringmaster = random.choice(malicious_nodes)  # Pick one malicious node as the leader

    #         total_weight = honest_count * 1 + num_malicious * ATTACKER_FACTOR

    #         for peer in self.peers.values():
    #             if peer.is_malicious:
    #                 if peer == ringmaster:
    #                     # Give the ringmaster all the malicious hash power
    #                     peer.hash_power = (num_malicious * ATTACKER_FACTOR) / total_weight
    #                 else:
    #                     # Other malicious nodes get 0 power (they don't mine)
    #                     peer.hash_power = 0
    #             else:
    #                 peer.hash_power = 1 / total_weight


    #     self.log_file.write(f"Honest nodes (slow & low CPU): {honest_count}\n")
    #     self.log_file.write(f"Malicious nodes (fast & high CPU): {num_malicious}\n")

    #     # Choose one malicious node at random as the ringmaster.
    #     if num_malicious > 0:
    #         ringmaster_id = random.choice(list(malicious_peers))
    #         self.peers[ringmaster_id].ringmaster = True
    #         self.log_file.write(f"Ringmaster (malicious) selected: Peer {ringmaster_id}\n")
    #     else:
    #         self.log_file.write("No malicious nodes present; no ringmaster selected.\n")

    #     # Initialize network (this will include the malicious overlay per network.py)
    #     self.network = Network(self.peers)

    #     # Create genesis block and assign to all peers.
    #     genesis_block = Block(miner_id='Satoshi', prev_block_id=None, transactions=[], timestamp=0)
    #     for peer in self.peers.values():
    #         peer.blockchain[genesis_block.block_id] = genesis_block
    #         peer.current_longest_chain.append(genesis_block)
    #     self.log_file.write("Simulation setup ended.\n\n")
    def setup(self):
        """
        Sets up the simulation:
          - Creates peers and assigns parameters (hash power, malicious flag, etc.).
          - Selects one malicious node as the ringmaster.
          - Initializes the network (including overlay among malicious nodes).
          - Creates and assigns the genesis block.
        """
        # Remove previous simulation output directory if it exists
        if os.path.exists(self.parent_dir):
            shutil.rmtree(self.parent_dir)
        os.makedirs(self.parent_dir, exist_ok=True)
        self.log_file = open(self.log_file_path, 'w')
        self.log_file.write("Simulation setup started.\n")

        # Create peers
        peer_ids = [str(i) for i in range(NUM_PEERS)]
        num_malicious = int(PERCENT_MALICIOUS * NUM_PEERS)
        malicious_peers = set(random.sample(peer_ids, num_malicious))

        for pid in peer_ids:
            is_malicious = pid in malicious_peers
            is_slow = not is_malicious
            is_low_cpu = not is_malicious
            peer = Peer(pid, is_slow, is_low_cpu, is_malicious=is_malicious)
            self.peers[pid] = peer

        honest_count = NUM_PEERS - num_malicious

        # Select a random malicious node as the ringmaster
        malicious_nodes = [peer for peer in self.peers.values() if peer.is_malicious]
        ringmaster = random.choice(malicious_nodes) if malicious_nodes else None

        # Ensure total_weight is never zero to prevent division errors
        total_weight = honest_count + num_malicious
        if total_weight == 0:
            raise ValueError("Total hash weight is zero. Adjust parameters to avoid this.")

        # Assign hash power: honest nodes get their fair share, ringmaster gets all malicious power
        for peer in self.peers.values():
            if peer.is_malicious:
                if peer == ringmaster:
                    peer.hash_power = (num_malicious ) / total_weight
                else:
                    peer.hash_power = 0  # Other malicious nodes do not mine
            else:
                peer.hash_power = 1 / total_weight  # Honest nodes get their fair share

        self.log_file.write(f"Honest nodes (slow & low CPU): {honest_count}\n")
        self.log_file.write(f"Malicious nodes (fast & high CPU): {num_malicious}\n")

        # Log ringmaster selection
        if ringmaster:
            ringmaster.ringmaster = True
            self.log_file.write(f"Ringmaster (malicious) selected: Peer {ringmaster.peer_id}\n")
        else:
            self.log_file.write("No malicious nodes present; no ringmaster selected.\n")

        # Initialize network (this will include the malicious overlay per network.py)
        self.network = Network(self.peers)

        # Create genesis block and assign to all peers
        genesis_block = Block(miner_id='Satoshi', prev_block_id=None, transactions=[], timestamp=0)
        for peer in self.peers.values():
            peer.blockchain[genesis_block.block_id] = genesis_block
            peer.current_longest_chain.append(genesis_block)

        self.log_file.write("Simulation setup ended.\n\n")

    def run(self):
        """
        Runs the simulation event loop.
        """
        self.log_file.write("Simulation started.\n")
        # Schedule initial transaction generation and mining for each peer.
        for peer in self.peers.values():
            interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
            event_time = self.current_time + interarrival_time
            if event_time <= SIMULATION_TIME:
                event = Event(event_time, EventType.GENERATE_TRANSACTION, peer.peer_id)
                self.network.schedule_event(self.event_queue, event)
            peer.schedule_block_mined(self.current_time, self.event_queue, self.network)

        last_log_time = 0
        # Main simulation loop.
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > SIMULATION_TIME:
                break
            self.current_time = event.time
            peer = self.peers[event.peer_id]
            # Add random jitter.
            self.current_time += np.random.uniform(0, 0.1)

            if event.event_type == EventType.GENERATE_TRANSACTION:
                peer.generate_transaction(self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_TRANSACTION:
                txn = event.kwargs['transaction']
                from_peer = event.kwargs['from_peer']
                peer.receive_transaction(txn, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.BLOCK_MINED:
                block = event.kwargs["block"]
                peer.block_mined(self.current_time, self.event_queue, self.network, block)
            elif event.event_type == EventType.HASH_BROADCAST:
                block_hash = event.kwargs['block_hash']
                sender = event.kwargs['sender']
                if event.kwargs.get('full_block'):
                    peer.receive_block(event.kwargs['full_block'], sender, self.current_time, self.event_queue, self.network)
                else:
                    peer.receive_hash(block_hash, sender, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.GET_REQUEST:
                requester = event.kwargs['requester']
                block_hash = event.kwargs['block_hash']
                peer.receive_get_request(requester, block_hash, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_BLOCK:
                block = event.kwargs['block']
                from_peer = event.kwargs['from_peer']
                peer.receive_block(block, from_peer, self.current_time, self.event_queue, self.network)

            if self.current_time - last_log_time >= self.log_interval:
                self.log_file.write(f"At time {self.current_time:.2f}, chain lengths:\n")
                for pid, p in self.peers.items():
                    chain_length = len(p.current_longest_chain)
                    last_block_id = p.current_longest_chain[-1].block_id[:6] if chain_length > 0 else 'None'
                    self.log_file.write(f"Peer {pid}: Chain length {chain_length}, Last Block ID: {last_block_id}\n")
                last_log_time = self.current_time

        self.log_file.write("Simulation ended.\n")
        if self.log_file:
            self.log_file.close()

if __name__ == "__main__":
    sim = Simulation()
    sim.setup()
    sim.run()
