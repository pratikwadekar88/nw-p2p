# network.py
import random, heapq
from config import *
from collections import deque

class Network:
    """
    Represents the P2P network.
    """
    def __init__(self, peers):
        self.peers = peers  # dict of peer_id -> Peer
        self.latencies = {}  # (peer_i, peer_j) -> latency parameters
        self.initialize_topology()
        self.initialize_latencies()
        self.initialize_overlay_network()

    def initialize_topology(self):
        """
        Connect peers ensuring a connected network with degree constraints.
        """
        peer_ids = list(self.peers.keys())
        connected = False
        attempt = 0
        max_attempts = 100
        while not connected and attempt < max_attempts:
            attempt += 1
            # Reset connections
            for peer in self.peers.values():
                peer.connections = []
            random.shuffle(peer_ids)
            # Connect in a ring to guarantee connectivity
            for i in range(len(peer_ids)):
                peer_a = peer_ids[i]
                peer_b = peer_ids[(i + 1) % len(peer_ids)]
                if peer_b not in self.peers[peer_a].connections:
                    self.peers[peer_a].connections.append(peer_b)
                if peer_a not in self.peers[peer_b].connections:
                    self.peers[peer_b].connections.append(peer_a)
            # Ensure each peer has between MIN_CONNECTIONS and MAX_CONNECTIONS
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
            degrees_ok = all(MIN_CONNECTIONS <= len(peer.connections) <= MAX_CONNECTIONS for peer in self.peers.values())
            if not degrees_ok or not connected:
                connected = False
        if not connected:
            raise Exception("Failed to create a connected network with desired degree constraints.")

    def is_connected(self):
        """
        Checks network connectivity.
        """
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
        """
        Initializes latencies for all direct connections.
        For malicious-to-malicious connections, if an overlay link exists, we use a low propagation delay (1ms to 10ms) and FAST_LINK_SPEED.
        Otherwise, for general communication, propagation delay is chosen uniformly between MIN_PROP_DELAY and MAX_PROP_DELAY.
        """
        for peer_i in self.peers.values():
            for peer_j_id in peer_i.connections:
                key = (peer_i.peer_id, peer_j_id)
                peer_j = self.peers[peer_j_id]
                # Check if both nodes are malicious and if we want to simulate overlay behavior.
                if peer_i.is_malicious and peer_j.is_malicious:
                    # For malicious-to-malicious connections, use low delay.
                    prop_delay = random.uniform(0.001, 0.01)  # 1ms to 10ms
                    link_speed = FAST_LINK_SPEED
                else:
                    # For all other connections, use general parameters.
                    prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                    # If either node is slow, use slow link speed; otherwise fast.
                    link_speed = SLOW_LINK_SPEED
                self.latencies[key] = {'prop_delay': prop_delay, 'link_speed': link_speed}

    def initialize_overlay_network(self):
        """
        Creates a separate overlay network among malicious nodes ensuring connectivity
        with degree constraints.

        For each malicious node:
          - First, connect them in a ring to guarantee connectivity.
          - Then add extra random overlay connections until each node has at least OVERLAY_MIN
            connections (up to OVERLAY_MAX, if possible).

        Overlay links use low propagation delays (1ms to 10ms) and FAST_LINK_SPEED.
        The overlay connections are stored in self.overlay_network, and corresponding latency entries
        are added to self.latencies.
        """
        # Define desired overlay degree constraints.
        OVERLAY_MIN = 3
        OVERLAY_MAX = 6

        # Get list of malicious node IDs.
        malicious_ids = [pid for pid, p in self.peers.items() if p.is_malicious]
        # If there are no malicious nodes, set overlay_network to an empty dict.
        if not malicious_ids:
            self.overlay_network = {}
            return

        # Initialize overlay_network dictionary.
        self.overlay_network = {pid: [] for pid in malicious_ids}

        # --- Step 1: Connect malicious nodes in a ring to guarantee connectivity ---
        random.shuffle(malicious_ids)
        for i in range(len(malicious_ids)):
            pid = malicious_ids[i]
            next_pid = malicious_ids[(i + 1) % len(malicious_ids)]
            if next_pid not in self.overlay_network[pid]:
                self.overlay_network[pid].append(next_pid)
            if pid not in self.overlay_network[next_pid]:
                self.overlay_network[next_pid].append(pid)
            # Set overlay latency for these links (1ms to 10ms)
            prop_delay = random.uniform(0.001, 0.01)
            self.latencies[(pid, next_pid)] = {'prop_delay': prop_delay, 'link_speed': FAST_LINK_SPEED}
            self.latencies[(next_pid, pid)] = {'prop_delay': prop_delay, 'link_speed': FAST_LINK_SPEED}

        # --- Step 2: Add extra random overlay connections until each malicious node has at least OVERLAY_MIN links ---
        for pid in malicious_ids:
            while len(self.overlay_network[pid]) < OVERLAY_MIN:
                # Select from malicious nodes not already connected to pid.
                possible = [other for other in malicious_ids if other != pid and other not in self.overlay_network[pid]]
                if not possible:
                    break  # No additional nodes available.
                new_connection = random.choice(possible)
                # Add symmetric connection.
                self.overlay_network[pid].append(new_connection)
                if pid not in self.overlay_network[new_connection]:
                    self.overlay_network[new_connection].append(pid)
                # Assign low overlay latency.
                prop_delay = random.uniform(0.001, 0.01)
                self.latencies[(pid, new_connection)] = {'prop_delay': prop_delay, 'link_speed': FAST_LINK_SPEED}
                self.latencies[(new_connection, pid)] = {'prop_delay': prop_delay, 'link_speed': FAST_LINK_SPEED}

        # --- Optional: Trim connections if any node exceeds OVERLAY_MAX links ---
        for pid in malicious_ids:
            while len(self.overlay_network[pid]) > OVERLAY_MAX:
                removed = random.choice(self.overlay_network[pid])
                self.overlay_network[pid].remove(removed)
                if pid in self.overlay_network[removed]:
                    self.overlay_network[removed].remove(pid)
                # Optionally, remove these latency entries:
                self.latencies.pop((pid, removed), None)
                self.latencies.pop((removed, pid), None)

    def calculate_latency(self, from_peer_id, to_peer_id, message_size=None):
        """
        Calculates latency for a message from from_peer_id to to_peer_id.
        If an overlay link exists in self.latencies, that is used.
        Otherwise, if both nodes are malicious, a low propagation delay (1-10ms) and fast link speed are used.
        Else, a general latency is used (MIN_PROP_DELAY to MAX_PROP_DELAY and SLOW_LINK_SPEED if either node is slow).
        """
        key = (from_peer_id, to_peer_id)
        if key in self.latencies:
            params = self.latencies[key]
        else:
            # Retrieve the two peers.
            from_peer = self.peers[from_peer_id]
            to_peer = self.peers[to_peer_id]
            # If both are malicious, use overlay-like parameters.
            if from_peer.is_malicious and to_peer.is_malicious:
                prop_delay = random.uniform(0.001, 0.01)  # 1ms to 10ms
                link_speed = FAST_LINK_SPEED
            else:
                # If either node is slow, use slow link speed; otherwise, fast.
                if from_peer.is_slow or to_peer.is_slow:
                    prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                    link_speed = SLOW_LINK_SPEED
                else:
                    prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
                    link_speed = FAST_LINK_SPEED
            params = {'prop_delay': prop_delay, 'link_speed': link_speed}

        # Convert message size from bytes to bits.
        msg_size = 0 if message_size is None else message_size * 8
        mean_dij = (96 * 1024) / params['link_speed']
        queuing_delay = random.expovariate(1 / mean_dij)
        latency = params['prop_delay'] + (msg_size / params['link_speed']) + queuing_delay
        return latency

    def schedule_event(self, event_queue, event):
        """
        Schedules an event in the event queue.
        """
        heapq.heappush(event_queue, event)
