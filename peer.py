# peer.py

import random
import heapq
from transaction import Transaction
from block import Block
from event import EventType, Event
from config import *
import copy  # For deep copying data structures

class Peer:
    def __init__(self, peer_id, is_slow, is_low_cpu):
        self.peer_id = peer_id
        self.is_slow = is_slow
        self.is_low_cpu = is_low_cpu
        self.connections = []  # List of connected peer IDs
        self.pending_transactions = {}  # txn_id -> Transaction
        self.received_transactions = set()
        self.blockchain = {}  # block_id -> Block
        self.current_longest_chain = []  # List of Blocks in the longest chain
        self.current_balances = {}  # Stores balances based on the current longest chain
        self.mining_event = None
        self.mining = False  # Indicates if the peer is currently mining
        self.hash_power = None  # Will be set later

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
        self.current_balances = balances.copy()

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

            # Broadcast the transaction to connected peers
            for neighbor_id in self.connections:
                delay = network.calculate_latency(self.peer_id, neighbor_id, txn)
                event_time = current_time + delay
                if event_time <= SIMULATION_TIME:
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
        if next_event_time <= SIMULATION_TIME:
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

            # Forward transaction to neighbors except the one it came from
            for neighbor_id in self.connections:
                if neighbor_id != from_peer:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, transaction)
                    event_time = current_time + delay
                    if event_time <= SIMULATION_TIME:
                        event = Event(
                            time=event_time,
                            event_type=EventType.RECEIVE_TRANSACTION,
                            peer_id=neighbor_id,
                            transaction=transaction,
                            from_peer=self.peer_id
                        )
                        network.schedule_event(event_queue, event)

    # Start mining
    def start_mining(self, current_time, event_queue, network):
        if self.mining:
            return  # Already mining

        self.mining = True
        total_hash_power = sum(peer.hash_power for peer in network.peers.values())
        mean_time = MEAN_BLOCK_INTERVAL / (self.hash_power / total_hash_power)
        mining_time = random.expovariate(1 / mean_time)
        event_time = current_time + mining_time
        if event_time <= SIMULATION_TIME:
            event = Event(
                time=event_time,
                event_type=EventType.BLOCK_MINED,
                peer_id=self.peer_id
            )
            self.mining_event = event
            network.schedule_event(event_queue, event)
        else:
            self.mining = False
            self.mining_event = None

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
                    if block_size + txn_size <= max_block_size - TRANSACTION_SIZE:
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

            # Add block to blockchain
            self.blockchain[block.block_id] = block

            # Update longest chain
            self.update_blockchain(block)
            print(f"Peer {self.peer_id} mined block {block.block_id[:6]} at time {current_time:.2f}")

            # Broadcast block to neighbors
            for neighbor_id in self.connections:
                delay = network.calculate_latency(self.peer_id, neighbor_id, block)
                event_time = current_time + delay
                if event_time <= SIMULATION_TIME:
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
            self.mining = False
            self.mining_event = None

    # Receive a block
    def receive_block(self, block, from_peer, current_time, event_queue, network):
        if block.block_id not in self.blockchain:
            # Validate block
            if self.validate_block(block):
                self.blockchain[block.block_id] = block

                # Remove transactions included in the block from pending_transactions
                for txn in block.transactions:
                    self.pending_transactions.pop(txn.txn_id, None)

                # Construct candidate chain
                candidate_chain = self.construct_chain(block)

                # Compare chain lengths
                current_chain_length = len(self.current_longest_chain)
                candidate_chain_length = len(candidate_chain)

                if candidate_chain_length > current_chain_length:
                    self.update_blockchain(block)
                    print(f"Peer {self.peer_id} switched to a longer chain at time {current_time:.2f}")
                    if self.mining_event:
                        self.mining = False
                        self.mining_event = None
                    self.start_mining(current_time, event_queue, network)
                elif candidate_chain_length == current_chain_length:
                    # Random tie-breaker
                    if random.choice([True, False]):
                        self.update_blockchain(block)
                        print(f"Peer {self.peer_id} switched to an equal-length chain at time {current_time:.2f}")
                        if self.mining_event:
                            self.mining = False
                            self.mining_event = None
                        self.start_mining(current_time, event_queue, network)

                # Forward block to neighbors except the one it came from
                for neighbor_id in self.connections:
                    if neighbor_id != from_peer:
                        delay = network.calculate_latency(self.peer_id, neighbor_id, block)
                        event_time = current_time + delay
                        if event_time <= SIMULATION_TIME:
                            event = Event(
                                time=event_time,
                                event_type=EventType.RECEIVE_BLOCK,
                                peer_id=neighbor_id,
                                block=block,
                                from_peer=self.peer_id
                            )
                            network.schedule_event(event_queue, event)

    # Validate a block
    def validate_block(self, block):
        # Check if previous block exists
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

    # Construct chain leading to a given block
    def construct_chain(self, block):
        chain = []
        current_block = block
        while current_block:
            chain.append(current_block)
            prev_block_id = current_block.prev_block_id
            current_block = self.blockchain.get(prev_block_id, None)
        chain.reverse()
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

    # Update the blockchain with a new block
    def update_blockchain(self, new_block):
        chain = self.construct_chain(new_block)
        self.current_longest_chain = copy.deepcopy(chain)
        self.recompute_balances()

    # Get the peer's current balance
    def calculate_balance(self):
        return self.current_balances.get(self.peer_id, INITIAL_BALANCE)
