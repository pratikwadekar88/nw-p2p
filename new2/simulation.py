# simulation.py

import heapq
import random
from peer import Peer
from event import EventType, Event
from network import Network
from config import *

class Simulation:
    def __init__(self):
        self.peers = {}  # peer_id -> Peer
        self.event_queue = []
        self.current_time = 0
        self.hash_power_total = 0

    def setup(self):
        # Initialize peers
        num_slow = int(PERCENT_SLOW * NUM_PEERS)
        num_low_cpu = int(PERCENT_LOW_CPU * NUM_PEERS)
        peer_ids = [str(i) for i in range(NUM_PEERS)]
        random.shuffle(peer_ids)
        slow_peers = set(peer_ids[:num_slow])
        low_cpu_peers = set(peer_ids[num_slow:num_slow + num_low_cpu])

        for pid in peer_ids:
            is_slow = pid in slow_peers
            is_low_cpu = pid in low_cpu_peers
            peer = Peer(pid, is_slow, is_low_cpu)
            self.peers[pid] = peer

        # Assign hash powers
        total_peers = len(self.peers)
        num_low_cpu = sum(1 for peer in self.peers.values() if peer.is_low_cpu)
        num_high_cpu = total_peers - num_low_cpu

        low_cpu_power = 1 / (10 * num_low_cpu + num_high_cpu)
        high_cpu_power = 10 * low_cpu_power

        for peer in self.peers.values():
            if peer.is_low_cpu:
                peer.hash_power = low_cpu_power
            else:
                peer.hash_power = high_cpu_power
            self.hash_power_total += peer.hash_power

        # Initialize network
        self.network = Network(self.peers)

    def run(self):
        # Schedule initial events
        for peer in self.peers.values():
            # Transaction generation
            interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
            event_time = self.current_time + interarrival_time
            event = Event(event_time, EventType.GENERATE_TRANSACTION, peer.peer_id)
            self.network.schedule_event(self.event_queue, event)
            # Start mining
            peer.start_mining(self.current_time, self.event_queue, self.network)

        # Run simulation loop
        while self.event_queue and self.current_time < SIMULATION_TIME:
            event = heapq.heappop(self.event_queue)
            self.current_time = event.time
            peer = self.peers[event.peer_id]

            if event.event_type == EventType.GENERATE_TRANSACTION:
                peer.generate_transaction(self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_TRANSACTION:
                transaction = event.kwargs['transaction']
                from_peer = event.kwargs['from_peer']
                peer.receive_transaction(transaction, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.BLOCK_MINED:
                peer.block_mined(self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_BLOCK:
                block = event.kwargs['block']
                from_peer = event.kwargs['from_peer']
                peer.receive_block(block, from_peer, self.current_time, self.event_queue, self.network)

    def collect_results(self):
        # Collect and write blockchain trees to files
        for peer_id, peer in self.peers.items():
            filename = f'blockchain_{peer_id}.txt'
            with open(filename, 'w') as f:
                for block in peer.blockchain.values():
                    f.write(f'Block ID: {block.block_id}, Prev ID: {block.prev_block_id}, Miner: {block.miner_id}, Time: {block.timestamp}\n')

    def visualize_blockchain(self, peer_id):
        # Use networkx or any other tool to visualize the blockchain tree
        pass  # Visualization code can be added here
