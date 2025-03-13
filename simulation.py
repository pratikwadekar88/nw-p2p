# simulation.py
import heapq
import os
import random
import shutil
import numpy as np
from block import Block
from peer import Peer
from event import EventType, Event
from network import Network
from config import *

class Simulation:
    def __init__(self):
        self.peers = {}       # peer_id -> Peer
        self.event_queue = []
        self.current_time = 0
        self.network_snapshots = []
        self.parent_dir = "simOut"
        self.log_file_path = os.path.join(self.parent_dir, 'simulation_log.txt')
        self.log_file = None
        self.log_interval = 50

    def setup(self):
        # Remove prior simulation output and create a new directory.
        if os.path.exists(self.parent_dir):
            shutil.rmtree(self.parent_dir)
        os.makedirs(self.parent_dir, exist_ok=True)
        self.log_file = open(self.log_file_path, 'w')
        self.log_file.write("Simulation setup started.\n")

        # Determine node properties.
        num_slow = int(PERCENT_SLOW * NUM_PEERS)
        num_low_cpu = int(PERCENT_LOW_CPU * NUM_PEERS)
        peer_ids = [str(i) for i in range(NUM_PEERS)]
        slow_peers = set(random.sample(peer_ids, num_slow))
        low_cpu_peers = set(random.sample(peer_ids, num_low_cpu))
        num_malicious = int(MALICIOUS_PERCENT * NUM_PEERS)
        malicious_peers = set(random.sample(peer_ids, num_malicious))

        for pid in peer_ids:
            # Malicious nodes are forced to be fast.
            if pid in malicious_peers:
                is_slow = False
                is_low_cpu = False
            else:
                is_slow = pid in slow_peers
                is_low_cpu = pid in low_cpu_peers
            peer = Peer(pid, is_slow, is_low_cpu)
            if pid in malicious_peers:
                peer.is_malicious = True
            self.peers[pid] = peer

        if malicious_peers:
            # Choose one malicious node to act as the ringmaster.
            ringmaster_id = random.choice(list(malicious_peers))
            self.peers[ringmaster_id].is_ringmaster = True
            self.log_file.write(f"Malicious ringmaster: Peer {ringmaster_id}\n")

        # Log counts.
        num_red = sum(1 for peer in self.peers.values() if peer.is_slow and peer.is_low_cpu)
        num_orange = sum(1 for peer in self.peers.values() if peer.is_slow and not peer.is_low_cpu)
        num_green = sum(1 for peer in self.peers.values() if not peer.is_slow and peer.is_low_cpu)
        num_blue = sum(1 for peer in self.peers.values() if not peer.is_slow and not peer.is_low_cpu)
        self.log_file.write(f"Red nodes (slow & low CPU): {num_red}\n")
        self.log_file.write(f"Orange nodes (slow only): {num_orange}\n")
        self.log_file.write(f"Green nodes (low CPU only): {num_green}\n")
        self.log_file.write(f"Blue nodes (fast & high CPU): {num_blue}\n")
        self.log_file.write(f"Malicious nodes: {len(malicious_peers)}\n")

        # Compute hash power.
        total_peers = len(self.peers)
        num_low_cpu_peers = sum(1 for peer in self.peers.values() if peer.is_low_cpu)
        num_high_cpu_peers = total_peers - num_low_cpu_peers
        low_cpu_power = 1 / (10 * num_high_cpu_peers + num_low_cpu_peers)
        high_cpu_power = 10 * low_cpu_power
        total_hash_power = 0
        for peer in self.peers.values():
            if peer.is_low_cpu:
                peer.hash_power = low_cpu_power
            else:
                peer.hash_power = high_cpu_power
            total_hash_power += peer.hash_power
        for peer in self.peers.values():
            peer.hash_power /= total_hash_power

        # Create network and the genesis block
        self.network = Network(self.peers)
        genesis_block = Block(miner_id='Satoshi', prev_block_id=None, transactions=[], timestamp=0)
        for peer in self.peers.values():
            peer.blockchain[genesis_block.block_id] = genesis_block
            peer.current_longest_chain.append(genesis_block)
        self.log_file.write("Simulation setup ended.\n\n")

    def run(self, Tt):
        """
        Run the simulation.
        Tt: timeout duration for GET requests (in seconds)
        """
        self.log_file.write("Simulation started.\n")
        # Schedule initial events for transaction generation and block mining.
        for peer in self.peers.values():
            interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
            event_time = self.current_time + interarrival_time
            if event_time <= SIMULATION_TIME:
                event = Event(event_time, EventType.GENERATE_TRANSACTION, peer.peer_id)
                self.network.schedule_event(self.event_queue, event)
            # Schedule block mining for each peer.
            peer.schedule_block_mined(self.current_time, self.event_queue, self.network)
            
        last_log_time = 0
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > SIMULATION_TIME:
                break
            self.current_time = event.time
            # Introduce a small random jitter to avoid synchronization issues.
            self.current_time += np.random.uniform(0, 0.1)
            peer = self.peers[event.peer_id]
            # Process events based on event type.
            if event.event_type == EventType.GENERATE_TRANSACTION:
                peer.generate_transaction(self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_TRANSACTION:
                txn = event.kwargs['transaction']
                from_peer = event.kwargs['from_peer']
                peer.receive_transaction(txn, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.BLOCK_MINED:
                peer.block_mined(self.current_time, self.event_queue, self.network, event.kwargs["block"])
            elif event.event_type == EventType.RECEIVE_BLOCK:
                blk = event.kwargs['block']
                from_peer = event.kwargs['from_peer']
                peer.receive_block(blk, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_HASH:
                blk_hash = event.kwargs['hash']
                from_peer = event.kwargs['from_peer']
                peer.receive_hash(self.current_time, self.event_queue, self.network, blk_hash, from_peer, Tt)
            elif event.event_type == EventType.GET_REQUEST:
                blk_hash = event.kwargs['hash']
                from_peer = event.kwargs['from_peer']
                peer.handle_get_request(self.current_time, self.event_queue, self.network, blk_hash, from_peer)
            elif event.event_type == EventType.BLOCK_RESPONSE:
                blk = event.kwargs['block']
                peer.receive_block_response(self.current_time, self.event_queue, self.network, blk, Tt)
            elif event.event_type == EventType.TIMEOUT_EVENT:
                blk_hash = event.kwargs['hash']
                peer.handle_timeout(self.current_time, self.event_queue, self.network, blk_hash, Tt)

            # Periodic logging of chain lengths.
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
            self.log_file = None

# If running as a standalone module, for example:
if __name__ == '__main__':
    import sys
    # Example: Accept Tt (timeout duration) as a command-line argument.
    if len(sys.argv) > 1:
        Tt = float(sys.argv[1])
    else:
        Tt = 1.0  # default timeout value in seconds
    sim = Simulation()
    sim.setup()
    sim.run(Tt)
