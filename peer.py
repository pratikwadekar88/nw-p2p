import random
from collections import defaultdict
from transaction import Transaction
from block import Block, Blockchain
from config import *

class Peer:
    def __init__(self, peer_id, is_slow, is_low_cpu):
        self.id = peer_id
        self.is_slow = is_slow
        self.is_low_cpu = is_low_cpu
        self.neighbors = []
        self.mempool = []
        self.blockchain = Blockchain()
        self.sent_transactions = defaultdict(set)  # {neighbor_id: set(tx_ids)}
        self.received_from = defaultdict(set)      # {tx_id: set(neighbor_ids)}
        self.mining_event = None

    def add_neighbor(self, peer):
        if peer not in self.neighbors:
            self.neighbors.append(peer)

    def generate_transaction(self, receiver, amount):
        if self.blockchain.utxo.get(self.id, 0) >= amount:
            tx = Transaction(self.id, receiver, amount)
            self._process_new_transaction(tx, None)
            return tx
        return None

    def _process_new_transaction(self, tx, sender):
        """Handle new transaction (either generated or received)"""
        if tx.id in self.received_from:
            return  # Already processed
            
        self.mempool.append(tx)
        self.received_from[tx.id] = set()
        if sender is not None:
            self.received_from[tx.id].add(sender.id)
        self._propagate_transaction(tx, sender)

    def _propagate_transaction(self, tx, sender):
        """Forward transaction to appropriate neighbors"""
        for neighbor in self.neighbors:
            # Don't send back to sender or already sent
            if neighbor == sender:
                continue
            if tx.id in self.sent_transactions[neighbor.id]:
                continue
                
            # Schedule propagation
            latency = self._calculate_latency(neighbor, tx.size * 8)
            event = Event(
                timestamp=current_time + latency,
                event_type="tx_propagate",
                callback=neighbor.receive_transaction,
                data={"tx": tx, "sender": self}
            )
            event_queue.schedule(event)
            self.sent_transactions[neighbor.id].add(tx.id)

    def receive_transaction(self, data):
        """Handle incoming transaction with sender info"""
        tx = data["tx"]
        sender = data["sender"]
        
        if tx.id not in self.received_from:
            self._process_new_transaction(tx, sender)
        elif sender.id not in self.received_from[tx.id]:
            self.received_from[tx.id].add(sender.id)

    # Rest of the class remains same as previous implementation
    # [Mining, block handling, etc...]