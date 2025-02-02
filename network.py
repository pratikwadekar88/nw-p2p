# network.py

import random
import heapq
from config import *
from event import Event
from collections import deque

class Network:
    """
    Represents the network of peers.

    Attributes:
        peers (dict): Dictionary of peer_id -> Peer.
        latencies (dict): Dictionary of (peer_id_i, peer_id_j) -> latency parameters.
    """
    def __init__(self, peers):
        """
        Initializes the network with the given peers.

        Args:
            peers (dict): Dictionary of peer_id -> Peer.
        """
        self.peers = peers  # Dict of peer_id -> Peer
        self.latencies = {}  # (peer_id_i, peer_id_j) -> latency parameters

        self.initialize_topology()
        self.initialize_latencies()

    def initialize_topology(self):
        """
        Initializes the network topology by connecting peers.
        """
        peer_ids = list(self.peers.keys())
        connected = False
        attempt = 0
        max_attempts = 100  # Prevent potential infinite loops

        while not connected and attempt < max_attempts:
            attempt += 1
            # Reset connections
            for peer in self.peers.values():
                peer.connections = []

            # Start by creating a connected backbone
            # Use a shuffled list to connect peers in a ring (guarantees connectivity)
            random.shuffle(peer_ids)
            for i in range(len(peer_ids)):
                peer_a = peer_ids[i]
                peer_b = peer_ids[(i + 1) % len(peer_ids)]
                # Add mutual connections
                if peer_b not in self.peers[peer_a].connections:
                    self.peers[peer_a].connections.append(peer_b)
                if peer_a not in self.peers[peer_b].connections:
                    self.peers[peer_b].connections.append(peer_a)

            # Now, ensure each peer has between MIN_CONNECTIONS and MAX_CONNECTIONS connections
            # Remaining possible peers for each peer
            for peer_id in peer_ids:
                peer = self.peers[peer_id]
                while len(peer.connections) < MIN_CONNECTIONS:
                    possible_peers = [pid for pid in peer_ids if pid != peer_id and pid not in peer.connections]
                    if not possible_peers:
                        break  # No more peers to connect
                    new_peer_id = random.choice(possible_peers)
                    # Add mutual connections
                    peer.connections.append(new_peer_id)
                    self.peers[new_peer_id].connections.append(peer_id)
                # Trim connections if exceeds MAX_CONNECTIONS
                if len(peer.connections) > MAX_CONNECTIONS:
                    # Remove extra connections randomly
                    extra_connections = len(peer.connections) - MAX_CONNECTIONS
                    for _ in range(extra_connections):
                        removed_peer_id = random.choice(peer.connections)
                        peer.connections.remove(removed_peer_id)
                        self.peers[removed_peer_id].connections.remove(peer_id)

            # After adjustments, check if graph is connected
            connected = self.is_connected()
            # Final check: Ensure all peers have between MIN_CONNECTIONS and MAX_CONNECTIONS connections
            degrees_correct = all(MIN_CONNECTIONS <= len(peer.connections) <= MAX_CONNECTIONS for peer in self.peers.values())
            if not degrees_correct or not connected:
                connected = False  # Restart the process

        if not connected:
            raise Exception("Failed to create a connected network with the desired degree constraints after multiple attempts.")

    def is_connected(self):
        """
        Checks if the network is connected.

        Returns:
            bool: True if the network is connected, False otherwise.
        """
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

    def initialize_latencies(self):
        """
        Initializes the latencies between connected peers.
        """
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

    def calculate_latency(self, from_peer_id, to_peer_id, message):
        """
        Calculates the latency between two peers for a given message.

        Args:
            from_peer_id (int): The ID of the sending peer.
            to_peer_id (int): The ID of the receiving peer.
            message (Message): The message being sent.

        Returns:
            float: The calculated latency.
        """
        key = (from_peer_id, to_peer_id)
        params = self.latencies.get(key)
        if not params:
            # Should not happen, but handle it
            prop_delay = random.uniform(MIN_PROP_DELAY, MAX_PROP_DELAY)
            link_speed = FAST_LINK_SPEED
        else:
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

    def schedule_event(self, event_queue, event):
        """
        Schedules an event in the event queue.

        Args:
            event_queue (list): The event queue.
            event (Event): The event to be scheduled.
        """
        heapq.heappush(event_queue, event)
