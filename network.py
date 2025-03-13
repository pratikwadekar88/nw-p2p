# network.py
import random
import heapq
from config import *
from collections import deque

class Network:
    def __init__(self, peers):
        self.peers = peers  # dict: peer_id -> Peer
        self.latencies = {} # (peer_i, peer_j) -> latency parameters
        self.initialize_topology()
        self.initialize_latencies()

    def initialize_topology(self):
        peer_ids = list(self.peers.keys())
        connected = False
        attempt = 0
        max_attempts = 100
        while not connected and attempt < max_attempts:
            attempt += 1
            for peer in self.peers.values():
                peer.connections = []
            random.shuffle(peer_ids)
            for i in range(len(peer_ids)):
                peer_a = peer_ids[i]
                peer_b = peer_ids[(i + 1) % len(peer_ids)]
                if peer_b not in self.peers[peer_a].connections:
                    self.peers[peer_a].connections.append(peer_b)
                if peer_a not in self.peers[peer_b].connections:
                    self.peers[peer_b].connections.append(peer_a)
            for peer_id in peer_ids:
                peer = self.peers[peer_id]
                while len(peer.connections) < MIN_CONNECTIONS:
                    possible_peers = [pid for pid in peer_ids if pid != peer_id and pid not in peer.connections]
                    if not possible_peers:
                        break
                    new_peer_id = random.choice(possible_peers)
                    peer.connections.append(new_peer_id)
                    self.peers[new_peer_id].connections.append(peer_id)
                if len(peer.connections) > MAX_CONNECTIONS:
                    extra = len(peer.connections) - MAX_CONNECTIONS
                    for _ in range(extra):
                        removed = random.choice(peer.connections)
                        peer.connections.remove(removed)
                        self.peers[removed].connections.remove(peer_id)
            connected = self.is_connected()
            degrees_correct = all(MIN_CONNECTIONS <= len(peer.connections) <= MAX_CONNECTIONS for peer in self.peers.values())
            if not degrees_correct or not connected:
                connected = False
        if not connected:
            raise Exception("Failed to create connected network with the desired degree constraints.")

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

    def initialize_latencies(self):
        for peer_i in self.peers.values():
            for peer_j_id in peer_i.connections:
                key = (peer_i.peer_id, peer_j_id)
                prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                peer_j = self.peers[peer_j_id]
                if peer_i.is_slow or peer_j.is_slow:
                    link_speed = SLOW_LINK_SPEED
                else:
                    link_speed = FAST_LINK_SPEED
                self.latencies[key] = {
                    'prop_delay': prop_delay,
                    'link_speed': link_speed
                }

    def calculate_latency(self, from_peer_id, to_peer_id, message):
        from_peer = self.peers[from_peer_id]
        to_peer = self.peers[to_peer_id]
        # If both nodes are malicious, use overlay network delays.
        if from_peer.is_malicious and to_peer.is_malicious:
            prop_delay = random.uniform(MALICIOUS_MIN_PROP_DELAY, MALICIOUS_MAX_PROP_DELAY)
            link_speed = FAST_LINK_SPEED
        else:
            key = (from_peer_id, to_peer_id)
            params = self.latencies.get(key)
            if not params:
                prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                link_speed = FAST_LINK_SPEED
            else:
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

    def schedule_event(self, event_queue, event):
        heapq.heappush(event_queue, event)

    # Optionally, you can add an update_topology() here if desired.
