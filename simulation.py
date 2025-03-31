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

    def setup(self):
        """
        Sets up simulation: creates peers, assigns hash power, network, and genesis block.
        """
        if os.path.exists(self.parent_dir):
            shutil.rmtree(self.parent_dir)
        os.makedirs(self.parent_dir, exist_ok=True)
        self.log_file = open(self.log_file_path, 'w')
        self.log_file.write("Simulation setup started.\n")

        peer_ids = [str(i) for i in range(NUM_PEERS)]
        num_malicious = int(PERCENT_MALICIOUS * NUM_PEERS)
        malicious_peers = set(random.sample(peer_ids, num_malicious))
        for pid in peer_ids:
            # Honest nodes: slow & low CPU; malicious nodes: fast & high CPU.
            is_malicious = pid in malicious_peers
            is_slow = not is_malicious
            is_low_cpu = not is_malicious
            peer = Peer(pid, is_slow, is_low_cpu, is_malicious=is_malicious)
            self.peers[pid] = peer

        honest_count = NUM_PEERS - num_malicious
        attacker_factor = 3.0  # malicious nodes have 3x mining power compared to honest ones
        total_weight = honest_count * 1 + num_malicious * attacker_factor
        for peer in self.peers.values():
            if peer.is_malicious:
                peer.hash_power = attacker_factor / total_weight
            else:
                peer.hash_power = 1 / total_weight

        self.log_file.write(f"Honest nodes (slow & low CPU): {honest_count}\n")
        self.log_file.write(f"Malicious nodes (fast & high CPU): {num_malicious}\n")

        self.network = Network(self.peers)

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
        for peer in self.peers.values():
            interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
            event_time = self.current_time + interarrival_time
            if event_time <= SIMULATION_TIME:
                event = Event(event_time, EventType.GENERATE_TRANSACTION, peer.peer_id)
                self.network.schedule_event(self.event_queue, event)
            peer.schedule_block_mined(self.current_time, self.event_queue, self.network)

        last_log_time = 0
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > SIMULATION_TIME:
                break
            self.current_time = event.time
            peer = self.peers[event.peer_id]
            self.current_time += np.random.uniform(0, 0.1)
            print(f"Processing event: {event.event_type.name} for Peer {peer.peer_id} at time {self.current_time:.2f}")

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
