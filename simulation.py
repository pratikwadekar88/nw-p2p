# simulation.py

import heapq
import os
import random
from peer import Peer
from event import EventType, Event
from network import Network
from config import *
import numpy as np
import shutil

class Simulation:
    def __init__(self):
        """
        Initializes the Simulation class with peers, event queue, current time, and network snapshots.
        """
        self.peers = {}  # peer_id -> Peer
        self.event_queue = []
        self.current_time = 0
        self.network_snapshots = []  # For capturing network snapshots (if needed)
        self.parent_dir = "simOut"
        self.log_file_path = os.path.join(self.parent_dir, 'simulation_log.txt')
        self.log_file = None
        self.log_interval = 50  # Adjust as needed

    def close_log_file(self):
        """
        Closes the log file.
        """
        if self.log_file:
            self.log_file.close()
            self.log_file = None
            
    def setup(self):
        """
        Sets up the simulation by initializing peers, assigning hash powers, and initializing the network.
        """
        # Check if the directory exists and remove it
        if os.path.exists(self.parent_dir):
            shutil.rmtree(self.parent_dir)
        os.makedirs(self.parent_dir, exist_ok=True)

        # Initialize log file
        self.log_file = open(self.log_file_path, 'w')
        self.log_file.write("Simulation setup started.\n")

        # Initialize peers
        num_slow = int(PERCENT_SLOW * NUM_PEERS)
        num_low_cpu = int(PERCENT_LOW_CPU * NUM_PEERS)
        peer_ids = [str(i) for i in range(NUM_PEERS)]

        # Assign slow and low CPU peers independently
        slow_peers = set(random.sample(peer_ids, num_slow))
        low_cpu_peers = set(random.sample(peer_ids, num_low_cpu))

        for pid in peer_ids:
            is_slow = pid in slow_peers
            is_low_cpu = pid in low_cpu_peers
            peer = Peer(pid, is_slow, is_low_cpu)
            self.peers[pid] = peer

        # Output counts for verification
        num_red = sum(1 for peer in self.peers.values() if peer.is_slow and peer.is_low_cpu)
        num_orange = sum(1 for peer in self.peers.values() if peer.is_slow and not peer.is_low_cpu)
        num_green = sum(1 for peer in self.peers.values() if not peer.is_slow and peer.is_low_cpu)
        num_blue = sum(1 for peer in self.peers.values() if not peer.is_slow and not peer.is_low_cpu)

        # Log the counts
        self.log_file.write(f"Red nodes (slow & low CPU): {num_red}\n")
        self.log_file.write(f"Orange nodes (slow only): {num_orange}\n")
        self.log_file.write(f"Green nodes (low CPU only): {num_green}\n")
        self.log_file.write(f"Blue nodes (fast & high CPU): {num_blue}\n")

        # Assign hash powers
        total_peers = len(self.peers)
        num_low_cpu_peers = sum(1 for peer in self.peers.values() if peer.is_low_cpu)
        num_high_cpu_peers = total_peers - num_low_cpu_peers

        # Calculate hash power per peer
        low_cpu_power = 1 / (10 * num_high_cpu_peers + num_low_cpu_peers)
        high_cpu_power = 10 * low_cpu_power

        # Assign hash power
        total_hash_power = 0
        for peer in self.peers.values():
            if peer.is_low_cpu:
                peer.hash_power = low_cpu_power
            else:
                peer.hash_power = high_cpu_power
            total_hash_power += peer.hash_power

        # Normalize hash powers to sum to 1
        for peer in self.peers.values():
            peer.hash_power /= total_hash_power

        # Initialize network
        self.network = Network(self.peers)

        self.log_file.write("Simulation setup ended.\n\n")

    def run(self):
        """
        Runs the simulation by scheduling initial events, processing events from the event queue, and logging periodically.
        """

        self.log_file.write("Simulation started.\n")

        # Schedule initial events
        for peer in self.peers.values():
            # Transaction generation
            interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
            event_time = self.current_time + interarrival_time
            if event_time <= SIMULATION_TIME:
                event = Event(event_time, EventType.GENERATE_TRANSACTION, peer.peer_id)
                self.network.schedule_event(self.event_queue, event)
            # Start mining
            peer.start_mining(self.current_time, self.event_queue, self.network)
            
        # Run simulation loop
        last_log_time = 0
        while self.event_queue:
            event = heapq.heappop(self.event_queue)
            if event.time > SIMULATION_TIME:
                break  # Exit the loop if the event occurs after the simulation time
            self.current_time = event.time
            peer = self.peers[event.peer_id]
            # Introduce random jitter to prevent synchronization
            self.current_time += np.random.uniform(0, 0.1)
            print(f"Processing event: {event.event_type} for Peer {peer.peer_id} at time {self.current_time:.2f}")
            # Process event
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

            # Periodic logging
            if self.current_time - last_log_time >= self.log_interval:
                self.log_file.write(f"At time {self.current_time:.2f}, chain lengths:")
                for pid, p in self.peers.items():
                    chain_length = len(p.current_longest_chain)
                    last_block_id = p.current_longest_chain[-1].block_id[:6] if chain_length > 0 else 'None'
                    self.log_file.write(f"Peer {pid}: Chain length {chain_length}, Last Block ID: {last_block_id}\n")
                last_log_time = self.current_time
    
        self.log_file.write("Simulation ended.\n")
        self.close_log_file()