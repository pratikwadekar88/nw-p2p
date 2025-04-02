import heapq
import random
from collections import deque
from config import *
 
class Network:
    def __init__(self, peers):
        self.peers = peers  # Dict of peer_id -> Peer
        self.latencies = {}  # (peer_id_i, peer_id_j) -> latency parameters
        self.initialize_topology()
        self.initialize_latencies()
        self.initialize_malicious_overlay()
 
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
                a = peer_ids[i]
                b = peer_ids[(i+1) % len(peer_ids)]
                if b not in self.peers[a].connections:
                    self.peers[a].connections.append(b)
                if a not in self.peers[b].connections:
                    self.peers[b].connections.append(a)
            for peer_id in peer_ids:
                peer = self.peers[peer_id]
                while len(peer.connections) < MIN_CONNECTIONS:
                    possible = [pid for pid in peer_ids if pid != peer_id and pid not in peer.connections]
                    if not possible:
                        break
                    new_pid = random.choice(possible)
                    peer.connections.append(new_pid)
                    self.peers[new_pid].connections.append(peer_id)
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
            raise Exception("Failed to create a connected network with desired degree constraints.")
 
    def is_connected(self):
        visited = set()
        to_visit = deque()
        start_peer = next(iter(self.peers))
        to_visit.append(start_peer)
        while to_visit:
            pid = to_visit.popleft()
            if pid not in visited:
                visited.add(pid)
                to_visit.extend(self.peers[pid].connections)
        return len(visited) == len(self.peers)
 
    def initialize_latencies(self):
        for peer_i in self.peers.values():
            for peer_j_id in peer_i.connections:
                key = (peer_i.peer_id, peer_j_id)
                peer_j = self.peers[peer_j_id]
                if peer_i.is_malicious and peer_j.is_malicious:
                    prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                    link_speed = FAST_LINK_SPEED
                else:
                    prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                    if peer_i.is_slow or peer_j.is_slow:
                        link_speed = SLOW_LINK_SPEED
                    else:
                        link_speed = FAST_LINK_SPEED
                self.latencies[key] = {'prop_delay': prop_delay, 'link_speed': link_speed}
 
    def initialize_malicious_overlay(self):
        # Build overlay network only for malicious nodes.
        malicious_ids = [peer.peer_id for peer in self.peers.values() if peer.is_malicious]
        MIN_OVERLAY = 3
        MAX_OVERLAY = 6
        for peer_id in malicious_ids:
            self.peers[peer_id].overlay_connections = []
        connected = False
        attempt = 0
        max_attempts = 100
        while not connected and attempt < max_attempts:
            attempt += 1
            for peer_id in malicious_ids:
                self.peers[peer_id].overlay_connections = []
            random.shuffle(malicious_ids)
            # Create a backbone ring among malicious nodes.
            for i in range(len(malicious_ids)):
                a = malicious_ids[i]
                b = malicious_ids[(i+1) % len(malicious_ids)]
                if b not in self.peers[a].overlay_connections:
                    self.peers[a].overlay_connections.append(b)
                if a not in self.peers[b].overlay_connections:
                    self.peers[b].overlay_connections.append(a)
            # Add extra overlay connections until each malicious node has at least MIN_OVERLAY.
            for peer_id in malicious_ids:
                peer = self.peers[peer_id]
                while len(peer.overlay_connections) < MIN_OVERLAY:
                    possible = [pid for pid in malicious_ids if pid != peer_id and pid not in peer.overlay_connections]
                    if not possible:
                        break
                    new_pid = random.choice(possible)
                    peer.overlay_connections.append(new_pid)
                    if peer_id not in self.peers[new_pid].overlay_connections:
                        self.peers[new_pid].overlay_connections.append(peer_id)
                if len(peer.overlay_connections) > MAX_OVERLAY:
                    extra = len(peer.overlay_connections) - MAX_OVERLAY
                    for _ in range(extra):
                        removed = random.choice(peer.overlay_connections)
                        peer.overlay_connections.remove(removed)
                        self.peers[removed].overlay_connections.remove(peer_id)
            connected = all(MIN_OVERLAY <= len(self.peers[pid].overlay_connections) <= MAX_OVERLAY for pid in malicious_ids)
        if not connected:
            raise Exception("Failed to create a malicious overlay network with desired degree constraints.")
 
    def calculate_latency(self, from_peer_id, to_peer_id, message):
        key = (from_peer_id, to_peer_id)
        from_peer = self.peers[from_peer_id]
        to_peer = self.peers[to_peer_id]
        # If both are malicious and overlay-connected, use fast overlay latency.
        if from_peer.is_malicious and to_peer.is_malicious:
            if hasattr(from_peer, 'overlay_connections') and to_peer_id in from_peer.overlay_connections:
                prop_delay = random.uniform(0.001, 0.01)  # 1-10ms overlay delay.
                link_speed = FAST_LINK_SPEED
            else:
                params = self.latencies.get(key)
                if not params:
                    prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                    link_speed = FAST_LINK_SPEED
                else:
                    prop_delay = params['prop_delay']
                    link_speed = params['link_speed']
        else:
            params = self.latencies.get(key)
            if not params:
                prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                link_speed = FAST_LINK_SPEED
            else:
                prop_delay = params['prop_delay']
                link_speed = params['link_speed']
        if hasattr(message, 'size'):
            msg_size = message.size * 8
        else:
            msg_size = 0
        mean_dij = (96 * 1024) / link_speed
        queuing_delay = random.expovariate(1 / mean_dij)
        return prop_delay + (msg_size / link_speed) + queuing_delay
 
    def schedule_event(self, event_queue, event):
        heapq.heappush(event_queue, event)
