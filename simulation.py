import heapq
import os
import random
from block import Block
from peer import Peer
from event import EventType, Event
from network import Network
from config import *
import numpy as np
import shutil

class Simulation:
    def __init__(self):
        self.peers = {}  # peer_id -> Peer
        self.event_queue = []
        self.current_time = 0
        self.network_snapshots = []
        self.parent_dir = "simOut"
        self.log_file_path = os.path.join(self.parent_dir, 'simulation_log.txt')
        self.log_file = None
        self.log_interval = 50
            
    def setup(self):
        if os.path.exists(self.parent_dir):
            shutil.rmtree(self.parent_dir)
        os.makedirs(self.parent_dir, exist_ok=True)
        self.log_file = open(self.log_file_path, 'w')
        self.log_file.write("Simulation setup started.\n")
        num_malicious = int(PERCENT_MALICIOUS * NUM_PEERS)
        peer_ids = [str(i) for i in range(NUM_PEERS)]
        malicious_peers = set(random.sample(peer_ids, num_malicious))
        for pid in peer_ids:
            # Note: if receive_transaction is not yet implemented in Peer, be sure to add it.
            peer = Peer(pid, is_malicious=(pid in malicious_peers))
            self.peers[pid] = peer

        num_honest = NUM_PEERS - num_malicious
        self.log_file.write(f"Honest nodes: {num_honest}\n")
        self.log_file.write(f"Malicious nodes: {num_malicious}\n")

        # --- Hashing Power Assignment ---
        base_power = 1.0
        for peer in self.peers.values():
            peer.hash_power = base_power
        malicious_list = [p for p in self.peers.values() if p.is_malicious]

        ringmaster = random.choice(malicious_list)
        ringmaster.is_ringmaster = True
        ringmaster.hash_power = p.hash_power * num_malicious
        for p in malicious_list:
            if not p.is_ringmaster:
                p.hash_power = 0.0
        self.log_file.write(f"Ringmaster is Peer {ringmaster.peer_id}\n")
        total_hash_power = sum(peer.hash_power for peer in self.peers.values())
        for peer in self.peers.values():
            peer.hash_power /= total_hash_power

        # Initialize the normal network topology.
        self.network = Network(self.peers)

        # Create and add the genesis block to every peer's blockchain.
        genesis_block = Block(miner_id='Satoshi', prev_block_id=None, transactions=[], timestamp=0)
        for peer in self.peers.values():
            peer.blockchain[genesis_block.block_id] = genesis_block
            peer.current_longest_chain.append(genesis_block)
        self.log_file.write("Simulation setup ended.\n\n")

    def run(self):
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
        next_broadcast_check = self.current_time
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > SIMULATION_TIME:
                break
            self.current_time = event.time
            peer = self.peers[event.peer_id]
            # Adding a slight processing delay.
            self.current_time += np.random.uniform(0, 0.1)
            print(f"Processing event: {event.event_type} for Peer {peer.peer_id} at time {self.current_time:.2f}")
            
            if event.event_type == EventType.GENERATE_TRANSACTION:
                peer.generate_transaction(self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_TRANSACTION:
                transaction = event.kwargs['transaction']
                from_peer = event.kwargs['from_peer']
                # Ensure the peer has implemented receive_transaction.
                peer.receive_transaction(transaction, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.BLOCK_MINED:
                # BLOCK_MINED events now carry the mined block in their kwargs.
                peer.block_mined(self.current_time, self.event_queue, self.network, event.kwargs["block"])
            elif event.event_type == EventType.RECEIVE_BLOCK:
                block = event.kwargs['block']
                from_peer = event.kwargs['from_peer']
                peer.receive_block(block, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RECEIVE_BLOCK_HASH:
                block_hash = event.kwargs['block_hash']
                block_is_malicious = event.kwargs.get('block_is_malicious', False)
                from_peer = event.kwargs['from_peer']
                peer.receive_block_hash(block_hash, block_is_malicious, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.GET_BLOCK_REQUEST:
                requester = event.kwargs['requester']
                block_hash = event.kwargs['block_hash']
                peer.handle_get_request(requester, block_hash, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.GET_BLOCK_RESPONSE:
                block = event.kwargs['block']
                from_peer = event.kwargs['from_peer']
                peer.receive_block_data(block, from_peer, self.current_time, self.event_queue, self.network)
            elif event.event_type == EventType.RINGMASTER_BROADCAST:
                # When a ringmaster broadcast event is processed, all malicious nodes with private chains broadcast them.
                for p in self.peers.values():
                    if p.is_malicious and p.private_chain:
                        p.broadcast_private_chain(self.current_time, self.event_queue, self.network)
                        
            # Check if it is time to consider a broadcast from the ringmaster.
            if self.current_time - next_broadcast_check >= 1:
                honest_chain_lengths = [len(p.current_longest_chain) for p in self.peers.values() if not p.is_malicious]
                global_honest_length = max(honest_chain_lengths) if honest_chain_lengths else 0
                ringmasters = [p for p in self.peers.values() if p.is_malicious and p.is_ringmaster]
                if ringmasters:
                    ringmaster = ringmasters[0]
                    private_len = len(ringmaster.private_chain)
                    if private_len > 0 and (global_honest_length == private_len or global_honest_length == private_len - 1):
                        event_broadcast = Event(self.current_time, EventType.RINGMASTER_BROADCAST, ringmaster.peer_id)
                        self.network.schedule_event(self.event_queue, event_broadcast)
                next_broadcast_check = self.current_time
            # Log simulation status periodically.
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
