# import random
# from collections import defaultdict
# from transaction import Transaction
# from block import Block, Blockchain
# from config import *
# from event import EventQueue, Event
# from datetime import datetime, timedelta
# # from main import current_time

# # Get the current time
# # current_time = datetime.now()
# event_queue = EventQueue()

# class Peer:
#     """Represents a peer in the P2P network."""
#     def __init__(self, peer_id, is_slow, is_low_cpu):
#         self.id = peer_id  # Unique peer ID
#         self.is_slow = is_slow  # Whether the peer is slow
#         self.is_low_cpu = is_low_cpu  # Whether the peer has low CPU power
#         self.neighbors = []  # Connected peers
#         self.mempool = []  # Unconfirmed transactions
#         self.blockchain = Blockchain()  # Local blockchain
#         self.sent_transactions = defaultdict(set)  # Transactions sent to neighbors
#         self.received_from = defaultdict(set)  # Neighbors that sent each transaction
#         self.mining_event = None  # Scheduled mining event
#         self.blockchain.utxo[self.id] = INITIAL_COINS

#     def add_neighbor(self, peer):
#         """Add a neighbor to the peer's connection list."""
#         if peer not in self.neighbors:
#             self.neighbors.append(peer)

#     # def generate_transaction(self, receiver, amount):
#     #     if self.blockchain.utxo.get(self.id, 0) >= amount:
#     #         tx = Transaction(self.id, receiver, amount)
#     #         # print(f"[DEBUG] Peer {self.id} generated transaction {tx.id} ({amount} coins to {receiver})") # Done
#     #         self._process_new_transaction(tx, self.id)
#     #         return tx
#     #     else:
#     #         print(f"[DEBUG] Peer {self.id} has insufficient balance for transaction")
#     #     return None

#     def generate_transaction(self, receiver, amount):
#         # Prevent self-transactions
#         if receiver == self.id:
#             print(f"[DEBUG] Peer {self.id} cannot send to self")
#             return None
#         if self.blockchain.utxo.get(self.id, 0) >= amount:
#             tx = Transaction(self.id, receiver, amount)
#             self._process_new_transaction(tx, self.id)
#             return tx
#         else:
#             print(f"[DEBUG] Peer {self.id} has insufficient balance")
#         return None

#     def _process_new_transaction(self, tx, sender):
#         """Process a new transaction (either generated or received)."""
#         if tx.id in self.received_from:
#             return  # Already processed
#         # print(f"[DEBUG] Peer {self.id} added transaction {tx.id} to mempool")    # Done
#         self.mempool.append(tx)
#         # print(len(self.mempool))
#         # for i in self.mempool:
#         #     print(i.id)

#         self.received_from[tx.id] = set()
#         if sender is not None:
#             # print(f"[DEBUG] Peer {self.id} received transaction {tx.id} from {sender}")
#             self.received_from[tx.id].add(sender)
#             # print(len(self.received_from[tx.id]))
#         self._propagate_transaction(tx, sender)

#     def _propagate_transaction(self, tx, sender):
#         """Forward a transaction to appropriate neighbors."""
#         for neighbor in self.neighbors:
#             # Don't send back to sender or already sent
#             if neighbor == sender:
#                 continue
#             if tx.id in self.sent_transactions[neighbor.id]:
#                 continue
                
#             # Schedule propagation
#             latency = self._calculate_latency(neighbor, tx.size * 8)
#             event = Event(
#                 timestamp=current_time +latency,
#                 event_type="tx_propagate",
#                 callback=neighbor.receive_transaction,
#                 data=tx
#             )
#             # print(f"[DEBUG] Peer {self.id} forwarding transaction {tx.id} to Peer {neighbor.id} (latency: {latency:.2f}s)") # Done
#             event_queue.schedule(event)
#             self.sent_transactions[neighbor.id].add(tx.id)

#     def receive_transaction(self, data):
#         """Handle an incoming transaction with sender info."""
#         tx = data
#         sender = tx.sender
         
#         # print(f"[DEBUG] Received transaction {tx.id} from {sender} (type: {type(sender)})")  # Debugging line
#         # print(f"[DEBUG] tx.id: {tx.id}")
#         # print(f"[DEBUG] self.received_from: {self.received_from}")
#         # print(f"[DEBUG] sender: {sender}")
 
#         if tx.id not in self.received_from:
#             print(f"[DEBUG] Peer {self.id} received transaction {tx.id} from {sender}")
#             self._process_new_transaction(tx, sender)
#         elif sender not in self.received_from[tx.id]:
#             print(f"[DEBUG] Peer {self.id} received transaction2 {tx.id} from {sender}")
#             self.received_from[tx.id].add(sender)


#     def _calculate_latency(self, neighbor, message_bits):
#         """Calculate latency for message transmission."""
#         # Propagation delay (speed of light)
#         rho = random.uniform(MIN_PROPAGATION_DELAY, MAX_PROPAGATION_DELAY)
        
#         # Link speed (5 Mbps if either peer is slow, else 100 Mbps)
#         if self.is_slow or neighbor.is_slow:
#             c = SLOW_LINK_SPEED
#         else:
#             c = FAST_LINK_SPEED
            
#         # Transmission delay (message size / link speed)
#         transmission_delay = message_bits / c
        
#         # Queuing delay (exponential distribution)
#         d = random.expovariate(c / (96 * 1024))  # Mean = 96kbits / c
        
#         return rho + transmission_delay + d


#     def mine_block(self, data=None):
#         # print(f"[DEBUG] Peer {self.id} started mining")
#         if self.mining_event is None:
#             # print(f"[DEBUG] Peer {self.id} already mining a block")
#             # Calculate mining time based on CPU power
#             mining_time = random.expovariate(1 / (SIM_PARAMS["block_interval"] / self.hash_power))
#             block = Block(
#                 prev_hash=self.blockchain.chain[-1].id,
#                 miner_id=self.id,
#                 transactions=self._select_transactions()
#             )
#             # Schedule broadcast
#             event = Event(
#                 timestamp=current_time + mining_time,
#                 event_type="block_mined",
#                 callback=self.broadcast_block,
#                 data=block
#             )
#             event_queue.schedule(event)
#             self.mining_event = event

#     # def _select_transactions(self):
#     #     """Select transactions from mempool that fit in the block."""
#     #     # print(f"[DEBUG] Peer {self.id} selecting transactions for block")
#     #     selected = []
#     #     # if len(selected) == 0:
#     #     #     print(f"[DEBUG] Peer {self.id} has no transactions to mine")
#     #     total_size = 1024  # 1KB for coinbase transaction
#     #     # print(type(self.mempool))
        
#     #     for tx in self.mempool:
#     #         print(f"[DEBUG] total_size: {total_size}, tx.size: {tx.size}, MAX_BLOCK_SIZE_BYTES: {MAX_BLOCK_SIZE_BYTES}")
#     #         if total_size + tx.size <= MAX_BLOCK_SIZE_BYTES:
#     #             selected.append(tx)
#     #             total_size += tx.size
#     #     # for sender in self.sender:
#     #     #     txs_to_send = {sender: [tx] for tx in selected}
#     #     # # print(f"[DEBUG] Peer {self.id} selected {len(selected)} transactions for block")
#     #     # for tx, sender in txs_to_send.items():
#     #     #     print(f"[DEBUG] Peer {sender.id} sends to {self.id}: {tx}")
#     #     #     event = Event(
#     #     #         timestamp=current_time + 100,  # Assuming 10 seconds to send
#     #     #         event_type="send_transaction",
#     #     #         callback=lambda tx: self.send_transactions[sender][tx]
#     #     #     )
#     #     #     event_queue.schedule(event)
#     #     return selected
#     def _select_transactions(self):
#         """Select transactions and remove from mempool"""
#         selected = []
#         total_size = 1024
#         # Iterate over a copy to safely modify original list
#         for tx in self.mempool[:]:  
#             if total_size + tx.size <= MAX_BLOCK_SIZE_BYTES:
#                 selected.append(tx)
#                 total_size += tx.size
#                 self.mempool.remove(tx)  # Critical fix
#         return selected

#     def broadcast_block(self, block):
#         for neighbor in self.neighbors:
#             latency = self._calculate_latency(neighbor, block.size * 8)
#             event = Event(
#                 timestamp=current_time + latency,
#                 event_type="block_propagate",
#                 callback=neighbor.receive_block,
#                 data={"block": block, "sender": self}  # Include sender
#             )
#             event_queue.schedule(event)

#     def receive_block(self, data):
#         """Handle incoming blocks correctly"""
#         block = data["block"]
#         sender = data["sender"]
#         print(f"[DEBUG] Peer {self.id} received block {block.id}")
        
#         if self.blockchain.add_block(block):
#             # Clear current mining event
#             self.mining_event = None  
#             self.mine_block()
#     @property
#     def hash_power(self):
#         """Return the peer's hashing power (10x for high CPU)."""
#         return 10 if not self.is_low_cpu else 1

# peer.py
import random
from collections import defaultdict
from transaction import Transaction
from block import  Blockchain
from config import *
from event import EventQueue, Event

event_queue = EventQueue()
class Peer:
    def __init__(self, peer_id, is_slow, is_low_cpu, hash_power):
        self.id = peer_id
        self.is_slow = is_slow
        self.is_low_cpu = is_low_cpu
        self.neighbors = []
        self.mempool = []
        self.blockchain = Blockchain()
        self.sent_transactions = defaultdict(set)
        self.received_from = defaultdict(set)
        self.mining_event = None
        self.hash_power = hash_power  # Normalized hashing power
        self.blockchain.utxo[self.id] = INITIAL_COINS

    def add_neighbor(self, peer):
        if peer not in self.neighbors:
            self.neighbors.append(peer)

    def generate_transaction(self, receiver, amount):
        if receiver == self.id or self.blockchain.utxo.get(self.id, 0) < amount:
            return None
        tx = Transaction(self.id, receiver, amount)
        self._process_new_transaction(tx, self.id)
        return tx

    def _process_new_transaction(self, tx, sender):
        if tx.id not in self.received_from:
            self.mempool.append(tx)
            self.received_from[tx.id] = set()
            if sender: self.received_from[tx.id].add(sender)
            self._propagate_transaction(tx, sender)

    def _propagate_transaction(self, tx, sender):
        for neighbor in self.neighbors:
            if neighbor.id == sender or tx.id in self.sent_transactions[neighbor.id]:
                continue
            latency = self._calculate_latency(neighbor, tx.size * 8)
            event = Event(
                timestamp=current_time + latency,
                event_type="tx_propagate",
                callback=neighbor.receive_transaction,
                data=tx
            )
            event_queue.schedule(event)
            self.sent_transactions[neighbor.id].add(tx.id)

    def _calculate_latency(self, neighbor, msg_bits):
        rho = random.uniform(MIN_PROPAGATION_DELAY, MAX_PROPAGATION_DELAY)
        c = SLOW_LINK_SPEED if self.is_slow or neighbor.is_slow else FAST_LINK_SPEED
        d = random.expovariate(c / (96 * 1024))
        return rho + (msg_bits / c) + d

    def mine_block(self, data=None):
        if not self.mining_event and self.blockchain.chain[-1].id == self.blockchain.longest_chain[-1].id:
            mining_time = random.expovariate(SIM_PARAMS["block_interval"] / self.hash_power)
            block = Block(
                prev_hash=self.blockchain.longest_chain[-1].id,
                miner_id=self.id,
                transactions=self._select_transactions()
            )
            event = Event(
                timestamp=current_time + mining_time,
                event_type="block_mined",
                callback=self.broadcast_block,
                data=block
            )
            self.mining_event = event
            event_queue.schedule(event)

    def _select_transactions(self):
        selected = []
        total_size = 1024
        for tx in self.mempool[:]:
            if total_size + tx.size <= MAX_BLOCK_SIZE_BYTES:
                selected.append(tx)
                total_size += tx.size
                self.mempool.remove(tx)
        return selected

    def broadcast_block(self, block):
        for neighbor in self.neighbors:
            latency = self._calculate_latency(neighbor, block.size * 8)
            event = Event(
                timestamp=current_time + latency,
                event_type="block_propagate",
                callback=neighbor.receive_block,
                data={"block": block, "sender": self}
            )
            event_queue.schedule(event)

    def receive_block(self, data):
        block = data["block"]
        if self.blockchain.add_block(block):
            self.mining_event = None
            self.mine_block()