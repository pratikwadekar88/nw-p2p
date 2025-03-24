# network.py
import random
from config import *
from collections import deque

class Network:
    def __init__(self, peers, is_malicious=False):
        self.peers = peers  # dict: peer_id -> Peer # dictionary of all peers in this network
        self.latencies = {} # (peer_i, peer_j) -> latency parameters
        self.is_malicious = is_malicious; # can be regular network or malicious
        if not is_malicious:
            self.initialize_topology()
            self.initialize_latencies()
        else:
            self.initialize_private_topology()
            self.initialize_private_latencies()


    def initialize_topology(self):
        peer_ids = list(self.peers.keys())
        connected = False
        attempt = 0
        max_attempts = 100   # Prevent potential infinite loops
        while not connected and attempt < max_attempts:
            attempt += 1
            # Reset connections
            for peer in self.peers.values():
                peer.connections = []

            # Start by creating a connected backbone
            # Use a shuffled list to connect peers in a ring
            # (guarantees connectivity)
            random.shuffle(peer_ids)
            for i in range(len(peer_ids)):
                peer_a = peer_ids[i]
                peer_b = peer_ids[(i + 1) % len(peer_ids)]
                # Add mutual connections
                if peer_b not in self.peers[peer_a].connections:
                    self.peers[peer_a].connections.append(peer_b)
                if peer_a not in self.peers[peer_b].connections:
                    self.peers[peer_b].connections.append(peer_a)

            # Now, ensure each peer has between
            # MIN_CONNECTIONS and MAX_CONNECTIONS connections
            # Remaining possible peers for each peer
            for peer_id in peer_ids:
                peer = self.peers[peer_id]
                while len(peer.connections) < MIN_CONNECTIONS:
                    possible_peers = [pid for pid in peer_ids if pid != peer_id and pid not in peer.connections]
                    if not possible_peers:
                        break
                    new_peer_id = random.choice(possible_peers)
                    # Add mutual connections
                    peer.connections.append(new_peer_id)
                    self.peers[new_peer_id].connections.append(peer_id)
                if len(peer.connections) > MAX_CONNECTIONS:
                    extra = len(peer.connections) - MAX_CONNECTIONS
                    for _ in range(extra):
                        removed = random.choice(peer.connections)
                        peer.connections.remove(removed)
                        self.peers[removed].connections.remove(peer_id)

            # After adjustments, check if graph is connected
            connected = self.is_connected()
            # Final check: Ensure all peers have between MIN_CONNECTIONS and MAX_CONNECTIONS connections
            degrees_correct = all(MIN_CONNECTIONS <= len(peer.connections) <= MAX_CONNECTIONS for peer in self.peers.values())
            if not degrees_correct or not connected:
                connected = False
        if not connected:
            raise Exception("Failed to create connected network with the desired degree constraints.")


# Initializes the network topology by connecting peers.
    def initialize_private_topology(self):
        peer_ids = list(self.peers.keys())
        connected = False
        attempt = 0
        max_attempts = 100   # Prevent potential infinite loops

        while not connected and attempt < max_attempts:
            attempt += 1
            # Reset connections
            for peer in self.peers.values():
                peer.private_connections = []
            
            # Start by creating a connected backbone
            # Use a shuffled list to connect peers in a ring
            # (guarantees connectivity)
            random.shuffle(peer_ids)
            for i in range(len(peer_ids)):
                peer_a = peer_ids[i]
                peer_b = peer_ids[(i + 1) % len(peer_ids)]
                # Add mutual connections
                if peer_b not in self.peers[peer_a].private_connections:
                    self.peers[peer_a].private_connections.append(peer_b)
                if peer_a not in self.peers[peer_b].private_connections:
                    self.peers[peer_b].private_connections.append(peer_a)

            # Now, ensure each peer has between
            # MIN_CONNECTIONS and MAX_CONNECTIONS connections
            # Remaining possible peers for each peer
            for peer_id in peer_ids:
                peer = self.peers[peer_id]
                while len(peer.private_connections) < MIN_CONNECTIONS:
                    possible_peers = [pid for pid in peer_ids if pid != peer_id and pid not in peer.private_connections]
                    if not possible_peers:
                        break
                    new_peer_id = random.choice(possible_peers)
                    # Add mutual connections
                    peer.private_connections.append(new_peer_id)
                    self.peers[new_peer_id].private_connections.append(peer_id)

                # Trim connections if exceeds MAX_CONNECTIONS
                if len(peer.private_connections) > MAX_CONNECTIONS:
                    # Remove extra connections randomly
                    extra = len(peer.private_connections) - MAX_CONNECTIONS
                    for _ in range(extra):
                        removed = random.choice(peer.private_connections)
                        peer.private_connections.remove(removed)
                        self.peers[removed].private_connections.remove(peer_id)

            # After adjustments, check if graph is connected
            connected = self.is_privately_connected()
            # Final check: Ensure all peers have between MIN_CONNECTIONS and MAX_CONNECTIONS connections
            degrees_correct = all(MIN_CONNECTIONS <= len(peer.private_connections) <= MAX_CONNECTIONS for peer in self.peers.values())
            if not degrees_correct or not connected:
                connected = False # Restart the process

        if not connected:
            raise Exception("Failed to create connected network with the desired degree constraints.")


    # Checks if the network is connected.
    def is_connected(self):
        visited = set()
        queue = deque()
        start_peer = next(iter(self.peers))
        queue.append(start_peer)
        while queue:
            pid = queue.popleft()
            if pid not in visited:
                visited.add(pid)
                queue.extend(self.peers[pid].connections)
        return len(visited) == len(self.peers)


    def is_privately_connected(self):
        visited = set()
        queue = deque()
        start_peer = next(iter(self.peers))
        queue.append(start_peer)
        while queue:
            pid = queue.popleft()
            if pid not in visited:
                visited.add(pid)
                queue.extend(self.peers[pid].private_connections)
        return len(visited) == len(self.peers)


    # Initializes the latencies between connected peers.
    def initialize_latencies(self):
        for peer_i in self.peers.values():
            for peer_j_id in peer_i.connections:
                peer_j = self.peers[peer_j_id]

                key = (peer_i.peer_id, peer_j_id)

                prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                if peer_i.is_slow or peer_j.is_slow:
                    link_speed = SLOW_LINK_SPEED
                else:
                    link_speed = FAST_LINK_SPEED

                self.latencies[key] = {
                    'prop_delay': prop_delay,
                    'link_speed': link_speed
                }  


    # Initializes the latencies between connected peers in private overlay network
    def initialize_private_latencies(self):
        for peer_i in self.peers.values():
            for peer_j_id in peer_i.private_connections:
                peer_j = self.peers[peer_j_id]

                key = (peer_i.peer_id, peer_j_id)

                # for malicious overlay network, propagation delay and link speed are both fast
                prop_delay = random.uniform(MALICIOUS_MIN_PROP_DELAY, MALICIOUS_MAX_PROP_DELAY)
                link_speed = FAST_LINK_SPEED

                self.latencies[key] = {
                    'prop_delay': prop_delay,
                    'link_speed': link_speed
                }


    def calculate_latency(self, from_peer_id, to_peer_id, message):
        key = (from_peer_id, to_peer_id)
        params = self.latencies.get(key)
        prop_delay = params['prop_delay']
        link_speed = params['link_speed']
        if hasattr(message, 'size'):
            msg_size = message.size * 8  # bytes to bits
        else:
            msg_size = 0
        mean_dij = (96 * 1024) / link_speed
        queuing_delay = random.expovariate(1 / mean_dij)
        latency = prop_delay + (msg_size / link_speed) + queuing_delay
        return latency
