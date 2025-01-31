# peer.py

import random
import heapq
from collections import deque
from transaction import Transaction
from block import Block
from event import EventType, Event
from config import *

class Peer:
    def __init__(self, peer_id, is_slow, is_low_cpu):
        self.peer_id = peer_id
        self.is_slow = is_slow
        self.is_low_cpu = is_low_cpu
        self.connections = []  # List of connected peers
        self.pending_transactions = {}  # txn_id -> Transaction
        self.received_transactions = set()
        self.blockchain = {}  # block_id -> Block
        self.hash_power = None  # Will be set later
        self.current_longest_chain = []
        self.current_balances = {}  # Stores balances based on the current longest chain
        self.mining_event = None
        self.mining = False  # Indicates if the peer is currently mining

    def __str__(self):
        return f"Peer {self.peer_id}"

    # Recompute balances based on the current longest chain
    def recompute_balances(self):
        balances = {}
        # Initialize balances
        for block in self.current_longest_chain:
            for txn in block.transactions:
                sender = txn.sender_id
                receiver = txn.receiver_id
                amount = txn.amount
                balances.setdefault(sender, INITIAL_BALANCE)
                balances.setdefault(receiver, INITIAL_BALANCE)
                balances[sender] -= amount
                balances[receiver] += amount
        self.current_balances = balances

    # Generate a transaction
    def generate_transaction(self, current_time, event_queue, network):
        receiver_id = random.choice([pid for pid in network.peers if pid != self.peer_id])
        amount = random.uniform(1, 10)

        # Get the sender's current balance
        sender_balance = self.current_balances.get(self.peer_id, INITIAL_BALANCE)

        if sender_balance >= amount:
            # Create a new transaction
            txn = Transaction(
                sender_id=self.peer_id,
                receiver_id=receiver_id,
                amount=amount
            )
            self.pending_transactions[txn.txn_id] = txn
            self.received_transactions.add(txn.txn_id)

            # Log transaction creation
            print(f"Peer {self.peer_id} generated transaction {txn.txn_id} at time {current_time:.2f}")

            # Broadcast the transaction to connected peers
            for neighbor_id in self.connections:
                delay = network.calculate_latency(self.peer_id, neighbor_id, txn)
                event_time = current_time + delay
                event = Event(
                    time=event_time,
                    event_type=EventType.RECEIVE_TRANSACTION,
                    peer_id=neighbor_id,
                    transaction=txn,
                    from_peer=self.peer_id
                )
                network.schedule_event(event_queue, event)
        else:
            # Insufficient balance; transaction cannot be created
            pass

        # Schedule the next transaction generation event
        interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
        next_event_time = current_time + interarrival_time
        next_event = Event(
            time=next_event_time,
            event_type=EventType.GENERATE_TRANSACTION,
            peer_id=self.peer_id
        )
        network.schedule_event(event_queue, next_event)

    # Receive a transaction
    def receive_transaction(self, transaction, from_peer, current_time, event_queue, network):
        if transaction.txn_id not in self.received_transactions:
            self.received_transactions.add(transaction.txn_id)
            self.pending_transactions[transaction.txn_id] = transaction

            # Log transaction reception
            print(f"Peer {self.peer_id} received transaction {transaction.txn_id} from Peer {from_peer} at time {current_time:.2f}")

            # Forward transaction to neighbors except the one it came from
            for neighbor_id in self.connections:
                if neighbor_id != from_peer:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, transaction)
                    event_time = current_time + delay
                    event = Event(
                        time=event_time,
                        event_type=EventType.RECEIVE_TRANSACTION,
                        peer_id=neighbor_id,
                        transaction=transaction,
                        from_peer=self.peer_id
                    )
                    network.schedule_event(event_queue, event)

    # Receive a block
    def receive_block(self, block, from_peer, current_time, event_queue, network):
        if block.block_id not in self.blockchain:
            # Validate block
            if self.validate_block(block):
                self.blockchain[block.block_id] = block

                # Remove transactions included in the block from pending_transactions
                for txn in block.transactions:
                    txn_id = txn.txn_id
                    if txn_id in self.pending_transactions:
                        del self.pending_transactions[txn_id]

                # Update longest chain
                self.update_blockchain(block)

                # Forward block to neighbors except the one it came from
                for neighbor_id in self.connections:
                    if neighbor_id != from_peer:
                        delay = network.calculate_latency(self.peer_id, neighbor_id, block)
                        event_time = current_time + delay
                        event = Event(
                            time=event_time,
                            event_type=EventType.RECEIVE_BLOCK,
                            peer_id=neighbor_id,
                            block=block,
                            from_peer=self.peer_id
                        )
                        network.schedule_event(event_queue, event)

                # Restart mining if current block extends the longest chain
                if not self.current_longest_chain or \
                   self.get_chain_length(block) > len(self.current_longest_chain):
                    # Update the longest chain and recompute balances
                    self.current_longest_chain = self.construct_chain(block)
                    self.recompute_balances()
                    # Cancel current mining event
                    if self.mining_event and self.mining_event in event_queue:
                        event_queue.remove(self.mining_event)
                        heapq.heapify(event_queue)
                    # Start mining on new chain
                    self.start_mining(current_time, event_queue, network)

    # Validate a block
    def validate_block(self, block):
        if block.prev_block_id and block.prev_block_id not in self.blockchain:
            return False
        # Build the chain up to the previous block
        chain = self.construct_chain_by_id(block.prev_block_id)
        balances = {}
        for blk in chain:
            for txn in blk.transactions:
                sender = txn.sender_id
                receiver = txn.receiver_id
                amount = txn.amount
                balances.setdefault(sender, INITIAL_BALANCE)
                balances.setdefault(receiver, INITIAL_BALANCE)
                balances[sender] -= amount
                balances[receiver] += amount
        # Validate transactions in the new block
        for txn in block.transactions:
            sender = txn.sender_id
            receiver = txn.receiver_id
            amount = txn.amount
            if sender == "0":  # Coinbase transaction
                balances.setdefault(receiver, INITIAL_BALANCE)
                balances[receiver] += amount
            else:
                balances.setdefault(sender, INITIAL_BALANCE)
                balances.setdefault(receiver, INITIAL_BALANCE)
                if balances[sender] >= amount:
                    balances[sender] -= amount
                    balances[receiver] += amount
                else:
                    return False  # Invalid transaction
        return True

    # Start mining
    def start_mining(self, current_time, event_queue, network):
        self.mining = True
        total_hash_power = sum(peer.hash_power for peer in network.peers.values())
        mean_time = MEAN_BLOCK_INTERVAL / (self.hash_power / total_hash_power)
        mining_time = random.expovariate(1 / mean_time)
        event_time = current_time + mining_time
        event = Event(
            time=event_time,
            event_type=EventType.BLOCK_MINED,
            peer_id=self.peer_id
        )
        self.mining_event = event
        network.schedule_event(event_queue, event)

    # Block mined
    def block_mined(self, current_time, event_queue, network):
        if self.mining:
            prev_block = self.current_longest_chain[-1] if self.current_longest_chain else None
            prev_block_id = prev_block.block_id if prev_block else None

            # Transactions already in the chain
            included_txns = set()
            for blk in self.current_longest_chain:
                included_txns.update(txn.txn_id for txn in blk.transactions)

            # Select new transactions
            transactions = []
            block_size = EMPTY_BLOCK_SIZE
            max_block_size = MAX_BLOCK_SIZE

            for txn_id, txn in list(self.pending_transactions.items()):
                if txn_id not in included_txns:
                    txn_size = txn.size
                    if block_size + txn_size <= max_block_size:
                        transactions.append(txn)
                        block_size += txn_size
                        # Remove from pending transactions
                        del self.pending_transactions[txn_id]
                    else:
                        break  # Block size limit reached

            # Add coinbase transaction
            coinbase_txn = Transaction("0", self.peer_id, COINBASE_AMOUNT)
            transactions.insert(0, coinbase_txn)
            block_size += TRANSACTION_SIZE  # Add size of coinbase transaction

            # Create new block
            block = Block(
                miner_id=self.peer_id,
                prev_block_id=prev_block_id,
                transactions=transactions,
                timestamp=current_time
            )
            block.size = block_size  # Set block size

            # Log block mining
            print(f"Peer {self.peer_id} mined block {block.block_id} at time {current_time:.2f} including transactions:")
            for txn in transactions:
                print(f"  TxnID: {txn.txn_id}, Sender: {txn.sender_id}, Receiver: {txn.receiver_id}, Amount: {txn.amount}")

            # Add block to blockchain
            self.blockchain[block.block_id] = block
            # Update longest chain and recompute balances
            self.current_longest_chain = self.construct_chain(block)
            self.recompute_balances()

            # Broadcast block to neighbors
            for neighbor_id in self.connections:
                delay = network.calculate_latency(self.peer_id, neighbor_id, block)
                event_time = current_time + delay
                event = Event(
                    time=event_time,
                    event_type=EventType.RECEIVE_BLOCK,
                    peer_id=neighbor_id,
                    block=block,
                    from_peer=self.peer_id
                )
                network.schedule_event(event_queue, event)

            # Start mining next block
            self.start_mining(current_time, event_queue, network)
            self.mining = False  # Reset mining flag

    # Construct chain leading to a given block
    def construct_chain(self, block):
        chain = []
        current_block = block
        while current_block:
            chain.insert(0, current_block)
            prev_block_id = current_block.prev_block_id
            current_block = self.blockchain.get(prev_block_id, None)
        return chain

    # Construct chain up to a block ID (used in validation)
    def construct_chain_by_id(self, block_id):
        chain = []
        current_block = self.blockchain.get(block_id, None)
        while current_block:
            chain.insert(0, current_block)
            prev_block_id = current_block.prev_block_id
            current_block = self.blockchain.get(prev_block_id, None)
        return chain

    # Get chain length
    def get_chain_length(self, block):
        length = 0
        current_block = block
        while current_block:
            length += 1
            current_block = self.blockchain.get(current_block.prev_block_id, None)
        return length

    # Update the blockchain with a new block
    def update_blockchain(self, new_block):
        chain = self.construct_chain(new_block)
        if len(chain) > len(self.current_longest_chain):
            self.current_longest_chain = chain
            self.recompute_balances()

    # Get the peer's current balance
    def calculate_balance(self):
        return self.current_balances.get(self.peer_id, INITIAL_BALANCE)
