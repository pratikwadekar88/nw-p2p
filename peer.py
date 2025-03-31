# peer.py
import random, copy, uuid
from block import Block
from transaction import Transaction
from event import EventType, Event
from config import *
import time

class Peer:
    """
    Represents a peer in the network.
    """
    def __init__(self, peer_id, is_slow, is_low_cpu, is_malicious=False):
        self.peer_id = peer_id
        self.is_slow = is_slow
        self.is_low_cpu = is_low_cpu
        self.is_malicious = is_malicious
        self.connections = []  # List of connected peer IDs
        self.pending_transactions = {}  # txn_id -> Transaction
        self.received_transactions = set()
        self.blockchain = {}  # block_id -> Block
        self.current_longest_chain = []  # List of Blocks in the longest chain
        self.current_balances = {}
        self.hash_power = None  # Will be set during simulation setup

        # For enhanced propagation (hash-based broadcast & GET requests)
        self.block_timers = {}  # { block_hash: { 'timer_start': time, 'pending_senders': [peer_ids] } }

        # For selfish mining: malicious nodes keep a private chain
        if self.is_malicious:
            self.private_chain = []  # List of privately mined blocks (not yet broadcast)

    def __str__(self):
        return f"Peer {self.peer_id}"

    def recompute_balances(self):
        """
        Recomputes balances based on the current longest chain.
        """
        balances = {}
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

    def generate_transaction(self, current_time, event_queue, network):
        """
        Generates a new transaction and schedules the next generation event.
        """
        receiver_id = random.choice([pid for pid in network.peers if pid != self.peer_id])
        amount = random.uniform(1, 10)
        sender_balance = self.current_balances.get(self.peer_id, INITIAL_BALANCE)
        if sender_balance >= amount:
            txn = Transaction(sender_id=self.peer_id, receiver_id=receiver_id, amount=amount)
            self.pending_transactions[txn.txn_id] = txn
            self.received_transactions.add(txn.txn_id)
            for neighbor_id in self.connections:
                delay = network.calculate_latency(self.peer_id, neighbor_id, message_size=txn.size)
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
        interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
        next_event_time = current_time + interarrival_time
        if next_event_time <= SIMULATION_TIME:
            next_event = Event(
                time=next_event_time,
                event_type=EventType.GENERATE_TRANSACTION,
                peer_id=self.peer_id
            )
            network.schedule_event(event_queue, next_event)

    def receive_transaction(self, transaction, from_peer, current_time, event_queue, network):
        """
        Receives and forwards a transaction.
        """
        if transaction.txn_id not in self.received_transactions:
            self.received_transactions.add(transaction.txn_id)
            self.pending_transactions[transaction.txn_id] = transaction
            for neighbor_id in self.connections:
                if neighbor_id != from_peer:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, message_size=transaction.size)
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

    def schedule_block_mined(self, current_time, event_queue, network):
        """
        Schedules a block mining event.
        """
        total_hash_power = sum(peer.hash_power for peer in network.peers.values())
        mean_time = MEAN_BLOCK_INTERVAL / (self.hash_power / total_hash_power)
        mining_time = random.expovariate(1 / mean_time)
        event_time = current_time + mining_time
        if event_time <= SIMULATION_TIME:
            prev_block = self.current_longest_chain[-1] if self.current_longest_chain else None
            prev_block_id = prev_block.block_id if prev_block else None
            included_txns = set()
            for blk in self.current_longest_chain:
                included_txns.update(txn.txn_id for txn in blk.transactions)
            transactions = []
            block_size = EMPTY_BLOCK_SIZE
            for txn_id, txn in list(self.pending_transactions.items()):
                if txn_id not in included_txns:
                    if block_size + txn.size <= MAX_BLOCK_SIZE - TRANSACTION_SIZE:
                        transactions.append(txn)
                        block_size += txn.size
                        del self.pending_transactions[txn_id]
                    else:
                        break
            coinbase_txn = Transaction("0", self.peer_id, COINBASE_AMOUNT)
            transactions.insert(0, coinbase_txn)
            block = Block(
                miner_id=self.peer_id,
                prev_block_id=prev_block_id,
                transactions=transactions,
                timestamp=current_time
            )
            event = Event(
                time=event_time,
                event_type=EventType.BLOCK_MINED,
                peer_id=self.peer_id,
                block=block
            )
            network.schedule_event(event_queue, event)

    def block_mined(self, current_time, event_queue, network, block):
        """
        Called when this peer mines a block.
        For honest nodes, the block is added and its hash is broadcast immediately.
        For malicious nodes, the block is added to a private chain.
        """
        candidate_chain = self.construct_chain(block)
        if len(candidate_chain) <= len(self.current_longest_chain):
            for txn in block.transactions:
                self.pending_transactions[txn.txn_id] = txn
        else:
            self.blockchain[block.block_id] = block
            if self.is_malicious:
                # Instead of broadcasting, add the block to the private chain.
                self.private_chain.append(block)
                print(f"Malicious peer {self.peer_id} mined a private block (private chain length: {len(self.private_chain)}) at time {current_time:.2f}")
                # Try to release private chain if conditions are met.
                self.try_release_private_chain(current_time, event_queue, network)
            else:
                self.update_blockchain(block)
                print(f"Honest peer {self.peer_id} mined block {block.block_id[:6]} at time {current_time:.2f}")
                self.broadcast_hash(block, current_time, event_queue, network)
        self.schedule_block_mined(current_time, event_queue, network)

    def try_release_private_chain(self, current_time, event_queue, network):
        """
        For a malicious node, release the private chain if its lead over the public (honest) chain is at least 1.
        Here, we define:
            lead = len(private_chain) - (len(current_longest_chain) - 1)
        If lead >= 1, the malicious node releases (broadcasts) all blocks in its private chain.
        """
        # Calculate the lead; subtracting 1 because the genesis block is common.
        lead = len(self.private_chain) - (len(self.current_longest_chain) - 1)
        if lead >= 1:
            print(f"Malicious peer {self.peer_id} releasing private chain of length {len(self.private_chain)} at time {current_time:.2f} (lead={lead})")
            for block in self.private_chain:
                self.update_blockchain(block)
                self.broadcast_hash(block, current_time, event_queue, network)
            self.private_chain = []

    def broadcast_hash(self, block, current_time, event_queue, network):
        """
        Broadcasts the block's hash to neighbors.
        Honest nodes broadcast hash and later respond to GET requests.
        Malicious nodes normally withhold until releasing private chain,
        except when responding for their own released blocks.
        """
        block_hash = block.block_id  # Using block_id as the hash for simplicity.
        for neighbor_id in self.connections:
            delay = network.calculate_latency(self.peer_id, neighbor_id, message_size=64)  # 64B hash
            event_time = current_time + delay
            if event_time <= SIMULATION_TIME:
                event = Event(
                    time=event_time,
                    event_type=EventType.HASH_BROADCAST,
                    peer_id=neighbor_id,
                    block_hash=block_hash,
                    sender=self.peer_id,
                    full_block=block if (self.is_malicious and block in self.current_longest_chain) else None
                )
                network.schedule_event(event_queue, event)

    def receive_hash(self, block_hash, from_peer, current_time, event_queue, network):
        """
        Handles reception of a block hash.
        """
        if block_hash in self.blockchain:
            return
        if block_hash not in self.block_timers:
            self.block_timers[block_hash] = {
                'timer_start': current_time,
                'pending_senders': [from_peer]
            }
            self.send_get_request(block_hash, from_peer, current_time, event_queue, network)
        else:
            self.block_timers[block_hash]['pending_senders'].append(from_peer)
            timer_start = self.block_timers[block_hash]['timer_start']
            if current_time - timer_start >= TIMEOUT_TT:
                chosen_sender = random.choice(self.block_timers[block_hash]['pending_senders'])
                self.send_get_request(block_hash, chosen_sender, current_time, event_queue, network)
                self.block_timers[block_hash]['timer_start'] = current_time

    def send_get_request(self, block_hash, target_peer, current_time, event_queue, network):
        """
        Sends a GET request for the full block data.
        """
        delay = network.calculate_latency(self.peer_id, target_peer, message_size=64)  # 64B GET request
        event_time = current_time + delay
        if event_time <= SIMULATION_TIME:
            event = Event(
                time=event_time,
                event_type=EventType.GET_REQUEST,
                peer_id=target_peer,
                requester=self.peer_id,
                block_hash=block_hash
            )
            network.schedule_event(event_queue, event)

    def receive_get_request(self, requester, block_hash, current_time, event_queue, network):
        """
        Handles an incoming GET request.
        Honest nodes send full block if available.
        Malicious nodes withhold honest block data (to enforce eclipse) but reply for their own blocks.
        """
        if block_hash in self.blockchain:
            block = self.blockchain[block_hash]
            if self.is_malicious and block.miner_id != self.peer_id:
                # Malicious node withholds honest block.
                return
            delay = network.calculate_latency(self.peer_id, requester, message_size=MAX_BLOCK_SIZE)
            event_time = current_time + delay
            if event_time <= SIMULATION_TIME:
                event = Event(
                    time=event_time,
                    event_type=EventType.RECEIVE_BLOCK,
                    peer_id=requester,
                    block=block,
                    from_peer=self.peer_id
                )
                network.schedule_event(event_queue, event)

    def receive_block(self, block, from_peer, current_time, event_queue, network):
        """
        Handles reception of a full block (e.g. after a GET request).
        """
        if block.block_id not in self.blockchain and self.validate_block(block):
            self.blockchain[block.block_id] = block
            candidate_chain = self.construct_chain(block)
            if len(candidate_chain) > len(self.current_longest_chain):
                self.update_blockchain(block)
                print(f"Peer {self.peer_id} updated chain with block {block.block_id[:6]} at time {current_time:.2f}")
                if not self.is_malicious:
                    self.broadcast_hash(block, current_time, event_queue, network)
                else:
                    # For malicious nodes, if an honest block arrives that diminishes their lead, abandon private chain.
                    if hasattr(self, 'private_chain') and self.private_chain:
                        lead = len(self.private_chain) - (len(self.current_longest_chain) - 1)
                        if lead < 1:
                            print(f"Malicious peer {self.peer_id} abandoning private chain due to honest block at time {current_time:.2f}")
                            self.private_chain = []
            self.block_timers.pop(block.block_id, None)

    def validate_block(self, block):
        """
        Validates a block by checking previous block existence and transactions.
        """
        if block.prev_block_id and block.prev_block_id not in self.blockchain:
            return False
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
        for txn in block.transactions:
            sender = txn.sender_id
            receiver = txn.receiver_id
            amount = txn.amount
            if sender == "0":  # Coinbase
                balances.setdefault(receiver, INITIAL_BALANCE)
                balances[receiver] += amount
            else:
                balances.setdefault(sender, INITIAL_BALANCE)
                balances.setdefault(receiver, INITIAL_BALANCE)
                if balances[sender] >= amount:
                    balances[sender] -= amount
                    balances[receiver] += amount
                else:
                    return False
        return True

    def construct_chain(self, block):
        """
        Constructs the chain leading to a given block.
        """
        chain = []
        current_block = block
        while current_block:
            chain.append(current_block)
            prev_block_id = current_block.prev_block_id
            current_block = self.blockchain.get(prev_block_id, None)
        chain.reverse()
        return chain

    def construct_chain_by_id(self, block_id):
        """
        Constructs the chain up to a given block ID.
        """
        chain = []
        current_block = self.blockchain.get(block_id, None)
        while current_block:
            chain.insert(0, current_block)
            prev_block_id = current_block.prev_block_id
            current_block = self.blockchain.get(prev_block_id, None)
        return chain

    def update_blockchain(self, new_block):
        """
        Updates the local blockchain with a new block.
        """
        chain = self.construct_chain(new_block)
        self.current_longest_chain = copy.deepcopy(chain)
        self.recompute_balances()

    def calculate_balance(self):
        """
        Returns the current balance for this peer.
        """
        return self.current_balances.get(self.peer_id, INITIAL_BALANCE)
