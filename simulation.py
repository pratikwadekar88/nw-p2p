# simulation.py
import os
import random
import shutil
import numpy as np
from event_queue import EventQueue
from block import Block
from peer import Peer
from event import EventType, Event
from network import Network
from config import *

class Simulation:
    def __init__(self):
        self.peers = {} # peer_id -> Peer
        self.malicious_peers = {}
        self.event_queue = EventQueue()
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
        num_slow = int(PERCENT_SLOW * NUM_PEERS) #  same as num of malicious
        num_fast = NUM_PEERS - num_slow
        num_low_cpu = int(PERCENT_LOW_CPU * NUM_PEERS)
        num_high_cpu = NUM_PEERS - num_low_cpu

        peer_ids = [str(i) for i in range(NUM_PEERS)]
        slow_peers = set(random.sample(peer_ids, num_slow)) # honest peers
        low_cpu_peers = set(random.sample(peer_ids, num_low_cpu))
        malicious_peers_set = set()

        for pid in peer_ids:
            is_slow = pid in slow_peers
            is_low_cpu = pid in low_cpu_peers
            peer = Peer(pid, is_slow, is_low_cpu)
            if not is_slow:
                peer.is_malicious = True
                malicious_peers_set.add(peer.peer_id)
            self.peers[pid] = peer

        # Choose one malicious node to act as the ringmaster.
        ringmaster_id = random.choice(list(malicious_peers_set))
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
        self.log_file.write(f"Malicious nodes: {len(malicious_peers_set)}\n")

        # Compute hash power.
        total_peers = len(self.peers)
        total_hash_power = (10 * num_fast + num_slow)
        low_cpu_power = 1 / total_hash_power
        high_cpu_power = 10 / total_hash_power
        malicious_power = 0
        for peer in self.peers.values():
            if peer.is_low_cpu:
                if not peer.is_malicious:
                    peer.hash_power = low_cpu_power
                else:
                    peer.hash_power = 0
                    malicious_power += low_cpu_power
            else:
                if not peer.is_malicious:
                    peer.hash_power = high_cpu_power
                else:
                    peer.hash_power = 0
                    malicious_power += low_cpu_power

        # give all malicious power to ringmaster
        self.peers[ringmaster_id].hash_power = malicious_power

        # for converting each hash power
        # for peer in self.peers.values():
        #     peer.hash_power /= total_hash_power

        # Create networks
        self.network = Network(self.peers)

        for peer_id, peer in self.peers.items():
            if peer.is_malicious:
                self.malicious_peers[peer_id] = peer

        self.overlay_network = Network(self.malicious_peers, is_malicious=True);

        # add the genesis block
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
                self.event_queue.schedule_event(event)
            # Schedule block mining for each peer.
            peer.schedule_block_mined(self.current_time, self.event_queue)
            
        last_log_time = 0
        while self.event_queue.eq:
            event = self.event_queue.get_event();
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
                if (peer.is_malicious):
                    peer.block_mined(self.current_time, self.event_queue, self.overlay_network, event.kwargs["block"])
                else:
                    peer.block_mined(self.current_time, self.event_queue, self.network, event.kwargs["block"])

            elif event.event_type == EventType.RECEIVE_HASH:
                blk_hash = event.kwargs['hash']
                from_peer = event.kwargs['from_peer']
                on_overlay = event.kwargs['overlay']
                if on_overlay:
                    peer.receive_hash(self.current_time, self.event_queue, self.overlay_network, blk_hash, from_peer, on_overlay, Tt)
                else:
                    peer.receive_hash(self.current_time, self.event_queue, self.network, blk_hash, from_peer, on_overlay, Tt)

            elif event.event_type == EventType.GET_REQUEST:
                blk_hash = event.kwargs['hash']
                from_peer = event.kwargs['from_peer']
                on_overlay = event.kwargs['overlay']
                if peer.is_malicious:
                    peer.handle_get_request(self.current_time, self.event_queue, self.network, self.overlay_network, blk_hash, from_peer, on_overlay)
                else:
                    peer.handle_get_request(self.current_time, self.event_queue, self.network, None, blk_hash, from_peer, on_overlay)

            elif event.event_type == EventType.RECEIVE_BLOCK:
                blk = event.kwargs['block']
                from_peer = event.kwargs['from_peer']
                on_overlay = event.kwargs['overlay']
                if peer.is_malicious:
                    peer.receive_block(self.current_time, self.event_queue, self.network, self.overlay_network, blk, from_peer, on_overlay, Tt)
                else:
                    peer.receive_block(self.current_time, self.event_queue, self.network, None, blk, from_peer, on_overlay, Tt)


            # elif event.event_type == EventType.RECEIVE_BLOCK:
            #     blk = event.kwargs['block']
            #     from_peer = event.kwargs['from_peer']
            #     peer.receive_block(blk, from_peer, self.current_time, self.event_queue, self.network)

            elif event.event_type == EventType.TIMEOUT_EVENT:
                blk_hash = event.kwargs['hash']
                from_peer = event.kwargs['from_peer']
                on_overlay = event.kwargs['overlay']
                if on_overlay:
                    peer.handle_timeout(self.current_time, self.event_queue, self.overlay_network, blk_hash, from_peer, on_overlay, Tt)
                else:
                    peer.handle_timeout(self.current_time, self.event_queue, self.network, blk_hash, from_peer, on_overlay, Tt)


            elif event.event_type == EventType.BROADCAST_PRIVATE_CHAIN: # this event always happens on overlay
                from_peer = event.kwargs['from_peer']
                broadcast_count = event.kwargs['broadcast_count']
                peer.broadcast_private_chain(self.current_time, self.event_queue, from_peer, self.network, self.overlay_network, broadcast_count)


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
