import random
from transaction import Transaction
from block import Block
from event import EventType, Event
from config import *
import copy  # For deep copying data structures

class Peer:
    """
    Represents a network node.

    Attributes:
        peer_id (str): Unique identifier.
        is_slow (bool): Honest nodes are slow; malicious nodes are forced fast.
        is_malicious (bool): True for malicious nodes.
        is_ringmaster (bool): True for the chosen malicious node that mines blocks.
        connections (list): Normal network connections (peer IDs).
        overlay_connections (list): Overlay network connections (for malicious nodes only).
        pending_transactions (dict): Pending transactions.
        received_transactions (set): Set of transaction IDs.
        blockchain (dict): Mapping block_id -> Block.
        current_longest_chain (list): List of Blocks representing the main chain.
        current_balances (dict): Account balances based on the chain.
        hash_power (float): Effective mining power.
        received_block_hashes (set): Set of seen block hashes.
        hash_request_timers (dict): Timer expiries for block data requests.
        pending_hash_senders (dict): Pending sender IDs for block requests.
        private_chain (list): Private chain maintained by malicious nodes.
    """
    def __init__(self, peer_id, is_malicious=False):
        # For honest nodes, is_slow is True; malicious nodes are forced fast.
        self.peer_id = peer_id
        self.is_slow = False if is_malicious else True  
        self.is_malicious = is_malicious
        self.is_ringmaster = False  # To be designated externally (in simulation setup)
        self.connections = []  # Normal network neighbors
        self.overlay_connections = []  # For malicious overlay network; set by the network
        self.pending_transactions = {}  # txn_id -> Transaction
        self.received_transactions = set()
        self.blockchain = {}  # block_id -> Block
        self.current_longest_chain = []  # Main chain (list of Blocks)
        self.current_balances = {}  # Balances computed from the chain
        self.hash_power = 1.0  # Default value (can be adjusted)
        self.received_block_hashes = set()
        self.hash_request_timers = {}  # Maps block hash -> timer expiry time
        self.pending_hash_senders = {}  # Maps block hash -> list of sender IDs
        self.private_chain = []  # For malicious nodes to hold blocks privately

    def __str__(self):
        return f"Peer {self.peer_id}"

    def recompute_balances(self):
        """
        Recompute account balances based on the current longest chain.
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
        Generates a new transaction and broadcasts it.
        """
        receiver_id = random.choice([pid for pid in network.peers if pid != self.peer_id])
        amount = random.uniform(1, 10)
        sender_balance = self.current_balances.get(self.peer_id, INITIAL_BALANCE)
        if sender_balance >= amount:
            txn = Transaction(sender_id=self.peer_id, receiver_id=receiver_id, amount=amount)
            self.pending_transactions[txn.txn_id] = txn
            self.received_transactions.add(txn.txn_id)
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
        interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
        next_event_time = current_time + interarrival_time
        if next_event_time <= SIMULATION_TIME:
            event = Event(
                time=next_event_time,
                event_type=EventType.GENERATE_TRANSACTION,
                peer_id=self.peer_id
            )
            network.schedule_event(event_queue, event)

    def receive_transaction(self, transaction, from_peer, current_time, event_queue, network):
        """
        Process an incoming transaction.
        If the transaction is new, add it to pending transactions and broadcast it to neighbors (except from_peer).
        """
        if transaction.txn_id in self.received_transactions:
            return
        self.received_transactions.add(transaction.txn_id)
        self.pending_transactions[transaction.txn_id] = transaction
        for neighbor_id in self.connections:
            if neighbor_id == from_peer:
                continue
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

    def schedule_block_mined(self, current_time, event_queue, network):
        """
        Starts the mining process for the peer.
        For malicious ringmaster nodes with selfish mining enabled, mined blocks are appended to a private chain and only their hashes
        are sent to other malicious peers via the fast overlay.
        """
        total_hash_power = sum(peer.hash_power for peer in network.peers.values())
        mean_time = MEAN_BLOCK_INTERVAL / (self.hash_power / total_hash_power) if self.hash_power > 0 else float('inf')
        mining_time = random.expovariate(1 / mean_time) if mean_time != float('inf') else float('inf')
        event_time = current_time + mining_time

        if event_time <= SIMULATION_TIME:
            prev_block = self.current_longest_chain[-1] if self.current_longest_chain else None
            prev_block_id = prev_block.block_id if prev_block else None

            included_txns = set(txn.txn_id for blk in self.current_longest_chain for txn in blk.transactions)
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
                timestamp=current_time,
                is_malicious=self.is_malicious
            )

            if self.is_malicious and SELFISH_MINING_ENABLED and self.is_ringmaster:
                # For selfish mining, the ringmaster appends the block to its private chain and only sends the block hash
                self.private_chain.append(block)
                block_hash = block.compute_hash()
                for neighbor_id in self.connections:
                    neighbor = network.peers[neighbor_id]
                    if neighbor.is_malicious and to_peer_in_overlay(self, neighbor):
                        delay = random.uniform(0.001, 0.01)  # Fast overlay delay (1-10ms)
                        event_time_overlay = current_time + delay
                        if event_time_overlay <= SIMULATION_TIME:
                            event = Event(
                                time=event_time_overlay,
                                event_type=EventType.RECEIVE_BLOCK_HASH,
                                peer_id=neighbor_id,
                                block_hash=block_hash,
                                block_is_malicious=block.is_malicious,
                                from_peer=self.peer_id
                            )
                            network.schedule_event(event_queue, event)
                # Honest nodes never receive the full block data from the malicious ringmaster.
            else:
                # Honest nodes or non-ringmaster malicious nodes broadcast the full block normally.
                self.blockchain[block.block_id] = block
                self.update_blockchain(block)
                block_hash = block.compute_hash()
                self.received_block_hashes.add(block_hash)
                for neighbor_id in self.connections:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, block_hash)
                    event_time_neighbor = current_time + delay
                    if event_time_neighbor <= SIMULATION_TIME:
                        event = Event(
                            time=event_time_neighbor,
                            event_type=EventType.RECEIVE_BLOCK_HASH,
                            peer_id=neighbor_id,
                            block_hash=block_hash,
                            block_is_malicious=block.is_malicious,
                            from_peer=self.peer_id
                        )
                        network.schedule_event(event_queue, event)

            # Schedule the next mining event by adding a BLOCK_MINED event with the block as part of kwargs.
            event_queue.append(Event(event_time, EventType.BLOCK_MINED, self.peer_id, block=block))

    def block_mined(self, current_time, event_queue, network, block):
        """
        Process a mined block event.
        """
        candidate_chain = self.construct_chain(block)
        if len(candidate_chain) <= len(self.current_longest_chain):
            # Reinsert transactions if the chain is not longer.
            for txn in block.transactions:
                self.pending_transactions[txn.txn_id] = txn
        else:
            self.blockchain[block.block_id] = block
            self.update_blockchain(block)
            print(f"Peer {self.peer_id} mined block {block.block_id[:6]} at time {current_time:.2f}")
            block_hash = block.compute_hash()
            self.received_block_hashes.add(block_hash)
            # Do not forward block hashes if a malicious node using an eclipse attack is withholding honest blocks.
            if not (self.is_malicious and ECLIPSE_ATTACK_ENABLED and not block.is_malicious):
                for neighbor_id in self.connections:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, block_hash)
                    event_time = current_time + delay
                    if event_time <= SIMULATION_TIME:
                        event = Event(
                            time=event_time,
                            event_type=EventType.RECEIVE_BLOCK_HASH,
                            peer_id=neighbor_id,
                            block_hash=block_hash,
                            block_is_malicious=block.is_malicious,
                            from_peer=self.peer_id
                        )
                        network.schedule_event(event_queue, event)
            # If this is a malicious ringmaster, check if we should broadcast the private chain.
            if self.is_malicious and SELFISH_MINING_ENABLED and self.is_ringmaster:
                public_len = len(self.current_longest_chain)
                private_len = len(self.private_chain)
                # Relaxed condition: broadcast if the public chain is at most 2 blocks longer than the private chain.
                if private_len > 0 and (public_len <= private_len + 2):
                    print(f"Ringmaster {self.peer_id} broadcasting private chain at time {current_time:.2f}")
                    self.broadcast_private_chain(current_time, event_queue, network)
            self.schedule_block_mined(current_time, event_queue, network)

    def receive_block_hash(self, block_hash, block_is_malicious, from_peer, current_time, event_queue, network):
        """
        Process reception of a block hash.
        For honest nodes, issue a GET request for full block data.
        Malicious nodes with eclipse attack enabled withhold honest blocks.
        """
        if self.is_malicious and ECLIPSE_ATTACK_ENABLED and not block_is_malicious:
            return
        if block_hash not in self.received_block_hashes:
            self.received_block_hashes.add(block_hash)
            self.hash_request_timers[block_hash] = current_time + DATA_REQUEST_TIMEOUT
            event = Event(
                time=current_time,
                event_type=EventType.GET_BLOCK_REQUEST,
                peer_id=from_peer,
                requester=self.peer_id,
                block_hash=block_hash
            )
            network.schedule_event(event_queue, event)
        else:
            if not self.has_full_block(block_hash):
                if block_hash not in self.hash_request_timers:
                    event = Event(
                        time=current_time,
                        event_type=EventType.GET_BLOCK_REQUEST,
                        peer_id=from_peer,
                        requester=self.peer_id,
                        block_hash=block_hash
                    )
                    network.schedule_event(event_queue, event)
                    self.hash_request_timers[block_hash] = current_time + DATA_REQUEST_TIMEOUT
                else:
                    self.pending_hash_senders.setdefault(block_hash, []).append(from_peer)

    def has_full_block(self, block_hash):
        """
        Checks if the full block corresponding to the given hash is present.
        """
        return any(block.compute_hash() == block_hash for block in self.blockchain.values())

    def receive_block_data(self, block, from_peer, current_time, event_queue, network):
        """
        Process reception of full block data (in response to a GET request).
        """
        block_hash = block.compute_hash()
        if block_hash in self.hash_request_timers:
            del self.hash_request_timers[block_hash]
        if block_hash in self.pending_hash_senders:
            del self.pending_hash_senders[block_hash]
        if block.block_id not in self.blockchain and self.validate_block(block):
            self.blockchain[block.block_id] = block
            for txn in block.transactions:
                self.pending_transactions.pop(txn.txn_id, None)
            candidate_chain = self.construct_chain(block)
            if len(candidate_chain) > len(self.current_longest_chain):
                self.update_blockchain(block)
                print(f"Peer {self.peer_id} updated chain after receiving block {block.block_id[:6]} at time {current_time:.2f}")
                self.schedule_block_mined(current_time, event_queue, network)
            if (not self.is_malicious) or (self.is_malicious and block.is_malicious):
                for neighbor_id in self.connections:
                    if neighbor_id != from_peer:
                        delay = network.calculate_latency(self.peer_id, neighbor_id, block_hash)
                        event_time = current_time + delay
                        if event_time <= SIMULATION_TIME:
                            event = Event(
                                time=event_time,
                                event_type=EventType.RECEIVE_BLOCK_HASH,
                                peer_id=neighbor_id,
                                block_hash=block_hash,
                                block_is_malicious=block.is_malicious,
                                from_peer=self.peer_id
                            )
                            network.schedule_event(event_queue, event)

    def handle_get_request(self, requester, block_hash, current_time, event_queue, network):
        """
        Process an incoming GET request for block data.
        For malicious nodes, if the requested block is honest, they withhold the full block.
        """
        for block in self.blockchain.values():
            if block.compute_hash() == block_hash:
                if self.is_malicious and not block.is_malicious:
                    return
                delay = network.calculate_latency(self.peer_id, requester, block)
                event_time = current_time + delay
                if event_time <= SIMULATION_TIME:
                    event = Event(
                        time=event_time,
                        event_type=EventType.GET_BLOCK_RESPONSE,
                        peer_id=requester,
                        block=block,
                        from_peer=self.peer_id
                    )
                    network.schedule_event(event_queue, event)
                break

    def check_hash_request_timeout(self, current_time, event_queue, network):
        """
        Checks for GET request timeouts and reissues requests if needed.
        """
        expired_hashes = [h for h, expiry in self.hash_request_timers.items() if current_time >= expiry]
        for block_hash in expired_hashes:
            for sender in self.pending_hash_senders.get(block_hash, []):
                event = Event(
                    time=current_time,
                    event_type=EventType.GET_BLOCK_REQUEST,
                    peer_id=sender,
                    requester=self.peer_id,
                    block_hash=block_hash
                )
                network.schedule_event(event_queue, event)
            self.hash_request_timers[block_hash] = current_time + DATA_REQUEST_TIMEOUT
            self.pending_hash_senders[block_hash] = []

    def receive_block(self, block, from_peer, current_time, event_queue, network):
        """
        Wrapper for processing full block data.
        """
        self.receive_block_data(block, from_peer, current_time, event_queue, network)

    def broadcast_private_chain(self, current_time, event_queue, network):
        """
        For malicious nodes: Upon receiving a broadcast command (from the ringmaster),
        each malicious node broadcasts its private chain (block hashes) to honest neighbors.
        """
        for block in self.private_chain:
            block_hash = block.compute_hash()
            for neighbor_id in self.connections:
                if not network.peers[neighbor_id].is_malicious:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, block_hash)
                    event_time = current_time + delay
                    if event_time <= SIMULATION_TIME:
                        event = Event(
                            time=event_time,
                            event_type=EventType.RECEIVE_BLOCK_HASH,
                            peer_id=neighbor_id,
                            block_hash=block_hash,
                            block_is_malicious=block.is_malicious,
                            from_peer=self.peer_id
                        )
                        network.schedule_event(event_queue, event)
        # Clear the private chain after broadcast.
        self.private_chain = []

    def validate_block(self, block):
        """
        Validates a block by checking the transactions and ensuring sufficient balances.
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
                    return False
        return True

    def construct_chain(self, block):
        """
        Constructs the chain leading to the specified block.
        """
        chain = []
        current_block = block
        while current_block:
            chain.append(current_block)
            current_block = self.blockchain.get(current_block.prev_block_id, None)
        chain.reverse()
        return chain

    def construct_chain_by_id(self, block_id):
        """
        Constructs the chain up to a block identified by block_id.
        """
        chain = []
        current_block = self.blockchain.get(block_id, None)
        while current_block:
            chain.insert(0, current_block)
            current_block = self.blockchain.get(current_block.prev_block_id, None)
        return chain

    def update_blockchain(self, new_block):
        """
        Updates the local blockchain and current longest chain with a new block.
        """
        chain = self.construct_chain(new_block)
        self.current_longest_chain = copy.deepcopy(chain)
        self.recompute_balances()

    def calculate_balance(self):
        """
        Returns the current balance of this peer.
        """
        return self.current_balances.get(self.peer_id, INITIAL_BALANCE)


def to_peer_in_overlay(from_peer, to_peer):
    """
    Utility function to check if two malicious peers are connected via the overlay network.
    """
    return hasattr(from_peer, 'overlay_connections') and (to_peer.peer_id in from_peer.overlay_connections)
