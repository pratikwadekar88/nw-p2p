# network.py

import random
import heapq
from config import *
from event import Event
from collections import deque
class Network:
    def __init__(self, peers):
        self.peers = peers  # Dict of peer_id -> Peer
        self.latencies = {}  # (peer_id_i, peer_id_j) -> latency parameters

        self.initialize_topology()
        self.initialize_latencies()

    # Initialize network topology
    def initialize_topology(self):
        peer_ids = list(self.peers.keys())
        connected = False
        while not connected:
            # Reset connections
            for peer in self.peers.values():
                peer.connections = []
            # Randomly connect peers
            for peer in self.peers.values():
                num_connections = random.randint(MIN_CONNECTIONS, MAX_CONNECTIONS)
                possible_peers = [pid for pid in peer_ids if pid != peer.peer_id]
                connections = random.sample(possible_peers, num_connections)
                peer.connections = list(set(peer.connections + connections))
                # Also add reverse connections
                for conn in connections:
                    self.peers[conn].connections.append(peer.peer_id)
            # Check if network is connected
            connected = self.is_connected()

    # Check if the network is connected
    def is_connected(self):
        visited = set()
        to_visit = deque()
        start_peer = next(iter(self.peers))
        to_visit.append(start_peer)
        while to_visit:
            peer_id = to_visit.popleft()
            if peer_id not in visited:
                visited.add(peer_id)
                to_visit.extend(self.peers[peer_id].connections)
        return len(visited) == len(self.peers)

    # Initialize latencies
    def initialize_latencies(self):
        for peer_i in self.peers.values():
            for peer_j_id in peer_i.connections:
                key = (peer_i.peer_id, peer_j_id)
                # ρij: Propagation delay
                prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                # c_ij: Link speed
                peer_j = self.peers[peer_j_id]
                if peer_i.is_slow or peer_j.is_slow:
                    link_speed = SLOW_LINK_SPEED
                else:
                    link_speed = FAST_LINK_SPEED
                # Store latency parameters
                self.latencies[key] = {
                    'prop_delay': prop_delay,
                    'link_speed': link_speed
                }

    # Calculate latency between two peers for a given message
    def calculate_latency(self, from_peer_id, to_peer_id, message):
        key = (from_peer_id, to_peer_id)
        params = self.latencies[key]
        prop_delay = params['prop_delay']
        link_speed = params['link_speed']
        # Message size in bits
        if hasattr(message, 'size'):
            msg_size = message.size * 8  # Bytes to bits
        else:
            msg_size = 0
        # dij: Queuing delay
        mean_dij = (96 * 1024) / link_speed
        queuing_delay = random.expovariate(1 / mean_dij)
        latency = prop_delay + (msg_size / link_speed) + queuing_delay
        return latency

    # Schedule event
    def schedule_event(self, event_queue, event):
        heapq.heappush(event_queue, event)
