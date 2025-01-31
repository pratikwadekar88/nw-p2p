# simulation.py

import heapq
import os
import random
from peer import Peer
from event import EventType, Event
from network import Network
from config import *
import networkx as nx
import matplotlib
matplotlib.use('TkAgg')  # or 'Qt5Agg' or 'Agg'
import matplotlib.pyplot as plt
import numpy as np
import shutil

class Simulation:
    def __init__(self):
        self.peers = {}  # peer_id -> Peer
        self.event_queue = []
        self.current_time = 0
        self.network_snapshots = []  # For capturing network snapshots (if needed)

    def setup(self):
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
        print(f"Red nodes (slow & low CPU): {num_red}")
        print(f"Orange nodes (slow only): {num_orange}")
        print(f"Green nodes (low CPU only): {num_green}")
        print(f"Blue nodes (fast & high CPU): {num_blue}")

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

    def run(self):
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
        log_interval = 50  # Adjust as needed
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
            if self.current_time - last_log_time >= log_interval:
                print(f"At time {self.current_time:.2f}, chain lengths:")
                for pid, p in self.peers.items():
                    chain_length = len(p.current_longest_chain)
                    last_block_id = p.current_longest_chain[-1].block_id[:6] if chain_length > 0 else 'None'
                    print(f"Peer {pid}: Chain length {chain_length}, Last Block ID: {last_block_id}")
                last_log_time = self.current_time

    def collect_results(self):
        parent_dir = "simOut"
        # Check if the directory exists and remove it
        if os.path.exists(parent_dir):
            shutil.rmtree(parent_dir)
        output_dir = "simOut/blockchainTxns"
        # Create the blockchainTxn directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Collect and write blockchain trees to files
        for peer_id, peer in self.peers.items():
            filename = os.path.join(output_dir, f'blockchain_{peer_id}.txt')
            with open(filename, 'w') as f:
                for block in peer.current_longest_chain:
                    f.write(f'Block ID: {block.block_id}\n')
                    f.write(f'Prev ID: {block.prev_block_id}\n')
                    f.write(f'Miner: {block.miner_id}\n')
                    f.write(f'Time: {block.timestamp}\n')
                    f.write('Transactions:\n')
                    for txn in block.transactions:
                        f.write(f'  TxnID: {txn.txn_id}, Sender: {txn.sender_id}, Receiver: {txn.receiver_id}, Amount: {txn.amount}\n')
                    f.write('\n')

    # Visualization of the blockchain tree for a specific peer
    def visualize_blockchain(self, peer_id, ax=None):
        peer = self.peers[peer_id]
        G = nx.DiGraph()

        # Add nodes and edges
        for block in peer.blockchain.values():
            G.add_node(block.block_id[:6], miner=block.miner_id, time=block.timestamp)
            if block.prev_block_id:
                G.add_edge(block.prev_block_id[:6], block.block_id[:6])

        # Use provided axes or create new
        if ax is None:
            plt.figure(figsize=(12, 8))
            ax = plt.gca()

        pos = nx.spring_layout(G, k=0.5, iterations=50)
        nx.draw(G, pos, with_labels=True, node_size=500, node_color='lightblue', arrowsize=20, ax=ax)

        # Add labels
        miner_labels = {node: f"Miner: {data['miner']}" for node, data in G.nodes(data=True)}
        nx.draw_networkx_labels(G, pos, labels=miner_labels, font_size=8, verticalalignment='bottom', font_color='red', ax=ax)

        ax.set_title(f'Blockchain Tree for Peer {peer_id}')
        ax.axis('off')
        
        # Specify the directory where you want to save the plot
        save_directory = 'simOut/plots/blockChainTrees'
        # Ensure the directory exists
        os.makedirs(save_directory, exist_ok=True)

        # Construct the full path
        save_path = os.path.join(save_directory, f'Peer {peer_id}.png')

        # Save the plot to the specified directory
        plt.savefig(save_path)
        plt.close()
        print(f'Plot saved to {save_path}')

    # Visualization of the network topology
    def visualize_network_topology(self):
        G = nx.Graph()

        # Add nodes with attributes
        for peer_id, peer in self.peers.items():
            G.add_node(peer_id, is_slow=peer.is_slow, is_low_cpu=peer.is_low_cpu)

        # Add edges
        for peer_id, peer in self.peers.items():
            for neighbor_id in peer.connections:
                G.add_edge(peer_id, neighbor_id)

        # Node colors based on attributes
        node_colors = []
        for node in G.nodes(data=True):
            is_slow = node[1]['is_slow']
            is_low_cpu = node[1]['is_low_cpu']
            if is_slow and is_low_cpu:
                node_colors.append('red')      # Slow and low CPU
            elif is_slow and not is_low_cpu:
                node_colors.append('orange')   # Slow only
            elif not is_slow and is_low_cpu:
                node_colors.append('green')    # Low CPU only
            else:
                node_colors.append('blue')     # Fast and high CPU

        # Draw the graph
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G, k=0.3)
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=500, font_size=8)
        plt.title('Network Topology of Peers')
        plt.axis('off')

        # Specify the directory where you want to save the plot
        save_directory = 'simOut/plots'
        # Ensure the directory exists
        os.makedirs(save_directory, exist_ok=True)

        # Construct the full path
        save_path = os.path.join(save_directory, 'Peer Network.png')

        # Save the plot to the specified directory
        plt.savefig(save_path)
        plt.close()
        print(f'Plot saved to {save_path}')

    # Method to compare peer blockchains
    def compare_peer_blockchains(self):
        blockchains = {}
        for peer_id, peer in self.peers.items():
            chain = [block.block_id for block in peer.current_longest_chain]
            blockchains[peer_id] = chain

        differences_found = False
        peer_ids = list(blockchains.keys())
        for i in range(len(peer_ids)):
            for j in range(i + 1, len(peer_ids)):
                peer_a = peer_ids[i]
                peer_b = peer_ids[j]
                if blockchains[peer_a] != blockchains[peer_b]:
                    print(f"Peers {peer_a} and {peer_b} have different blockchains.")
                    print(f"Peer {peer_a} chain length: {len(blockchains[peer_a])}, chain: {blockchains[peer_a]}")
                    print(f"Peer {peer_b} chain length: {len(blockchains[peer_b])}, chain: {blockchains[peer_b]}")
                    differences_found = True
                    # Optionally break here to stop at first difference

        if not differences_found:
            print("All peers have identical blockchains.")
        else:
            print("Peers have divergent blockchains.")
