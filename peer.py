# peer.py
import random
import copy
import numpy as np
from transaction import Transaction
from block import Block
from event import EventType, Event
from config import *

class Peer:
    def __init__(self, peer_id, is_slow, is_low_cpu):
        self.peer_id = peer_id
        self.is_slow = is_slow
        self.is_low_cpu = is_low_cpu
        self.connections = []             # list of peer IDs
        self.pending_transactions = {}    # txn_id -> Transaction
        self.received_transactions = set()
        self.blockchain = {}              # block_id -> Block
        self.current_longest_chain = []   # list of Blocks (the main chain)
        self.current_balances = {}
        self.hash_power = None

        # Fields for enhanced propagation (two-step block delivery)
        self.known_hashes = {}            # block_hash -> Block (if full block already received)
        self.pending_hash_requests = {}   # block_hash -> { 'timer': float, 'requested_from': [peer_ids] }
        
        # Fields for selfish mining & eclipse attack simulation.
        self.is_malicious = False         # default honest; set in Simulation.setup()
        self.is_ringmaster = False        # for malicious ringmaster only
        self.private_chain = []           # for maintaining a private chain when selfish mining

    def __str__(self):
        return f"Peer {self.peer_id}"

    def recompute_balances(self):
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
        receiver_id = random.choice([pid for pid in network.peers if pid != self.peer_id])
        amount = random.uniform(1, 10)
        sender_balance = self.current_balances.get(self.peer_id, INITIAL_BALANCE)
        if sender_balance >= amount:
            txn = Transaction(sender_id=self.peer_id, receiver_id=receiver_id, amount=amount)
            self.pending_transactions[txn.txn_id] = txn
            self.received_transactions.add(txn.txn_id)
            for neighbor_id in self.connections:
                delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': TRANSACTION_SIZE}))
                event_time = current_time + delay
                if event_time <= SIMULATION_TIME:
                    event = Event(time=event_time, event_type=EventType.RECEIVE_TRANSACTION, 
                                  peer_id=neighbor_id, transaction=txn, from_peer=self.peer_id)
                    network.schedule_event(event_queue, event)
        interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
        next_event_time = current_time + interarrival_time
        if next_event_time <= SIMULATION_TIME:
            next_event = Event(time=next_event_time, event_type=EventType.GENERATE_TRANSACTION, peer_id=self.peer_id)
            network.schedule_event(event_queue, next_event)

    def receive_transaction(self, transaction, from_peer, current_time, event_queue, network):
        if transaction.txn_id not in self.received_transactions:
            self.received_transactions.add(transaction.txn_id)
            self.pending_transactions[transaction.txn_id] = transaction
            for neighbor_id in self.connections:
                if neighbor_id != from_peer:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': TRANSACTION_SIZE}))
                    event_time = current_time + delay
                    if event_time <= SIMULATION_TIME:
                        event = Event(time=event_time, event_type=EventType.RECEIVE_TRANSACTION, 
                                      peer_id=neighbor_id, transaction=transaction, from_peer=self.peer_id)
                        network.schedule_event(event_queue, event)

    def schedule_block_mined(self, current_time, event_queue, network):
        total_hash_power = sum(peer.hash_power for peer in network.peers.values())
        mean_time = MEAN_BLOCK_INTERVAL / (self.hash_power / total_hash_power)
        mining_time = random.expovariate(1 / mean_time)
        event_time = current_time + mining_time
        if event_time <= SIMULATION_TIME:
            prev_block = self.current_longest_chain[-1] if self.current_longest_chain else None
            prev_block_id = prev_block.block_id if prev_block else None

            # Prepare transactions for the new block.
            included_txns = set()
            for blk in self.current_longest_chain:
                included_txns.update(txn.txn_id for txn in blk.transactions)
            transactions = []
            block_size = EMPTY_BLOCK_SIZE
            for txn_id, txn in list(self.pending_transactions.items()):
                if txn_id not in included_txns:
                    txn_size = txn.size
                    if block_size + txn_size <= MAX_BLOCK_SIZE - TRANSACTION_SIZE:
                        transactions.append(txn)
                        block_size += txn_size
                        del self.pending_transactions[txn_id]
                    else:
                        break
            # Coinbase transaction.
            coinbase_txn = Transaction("0", self.peer_id, COINBASE_AMOUNT)
            transactions.insert(0, coinbase_txn)
            block = Block(miner_id=self.peer_id, prev_block_id=prev_block_id, transactions=transactions, timestamp=current_time)
            event = Event(time=event_time, event_type=EventType.BLOCK_MINED, peer_id=self.peer_id, block=block)
            network.schedule_event(event_queue, event)

    def block_mined(self, current_time, event_queue, network, block):
        """
        Revised block_mined function with detailed tie-breaker logic.
        """
        candidate_chain = self.construct_chain(block)
        current_chain_length = len(self.current_longest_chain)
        candidate_chain_length = len(candidate_chain)
        
        if candidate_chain_length < current_chain_length:
            # Block did not extend the chain; requeue its transactions.
            for txn in block.transactions:
                self.pending_transactions[txn.txn_id] = txn
            print(f"Peer {self.peer_id} rejected block {block.block_id[:6]} at time {current_time:.2f} (chain too short)")
        
        elif candidate_chain_length == current_chain_length:
            # Equal-length chain, tie-breaker.
            if random.choice([True, False]):
                self.blockchain[block.block_id] = block
                self.update_blockchain(block)
                print(f"Peer {self.peer_id} switched to an equal-length chain with block {block.block_id[:6]} at time {current_time:.2f}")
                self.broadcast_block_hash(current_time, event_queue, network, block)
            else:
                for txn in block.transactions:
                    self.pending_transactions[txn.txn_id] = txn
                print(f"Peer {self.peer_id} ignored equal-length block {block.block_id[:6]} at time {current_time:.2f}")
        
        else:  # candidate_chain_length > current_chain_length
            self.blockchain[block.block_id] = block
            self.update_blockchain(block)
            print(f"Peer {self.peer_id} extended chain with block {block.block_id[:6]} at time {current_time:.2f}")
            self.broadcast_block_hash(current_time, event_queue, network, block)
        
        # Always schedule new mining event for continuous block creation.
        self.schedule_block_mined(current_time, event_queue, network)

    def receive_block(self, block, from_peer, current_time, event_queue, network):
        if block.block_id not in self.blockchain:
            if self.validate_block(block):
                self.blockchain[block.block_id] = block
                for txn in block.transactions:
                    self.pending_transactions.pop(txn.txn_id, None)
                candidate_chain = self.construct_chain(block)
                current_chain_length = len(self.current_longest_chain)
                if len(candidate_chain) > current_chain_length:
                    self.update_blockchain(block)
                    print(f"Peer {self.peer_id} switched to a longer chain at time {current_time:.2f}")
                    self.schedule_block_mined(current_time, event_queue, network)
                elif len(candidate_chain) == current_chain_length:
                    if random.choice([True, False]):
                        self.update_blockchain(block)
                        print(f"Peer {self.peer_id} switched to an equal-length chain at time {current_time:.2f}")
                        self.schedule_block_mined(current_time, event_queue, network)
                for neighbor_id in self.connections:
                    if neighbor_id != from_peer:
                        delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': MAX_BLOCK_SIZE}))
                        event_time = current_time + delay
                        event = Event(time=event_time, event_type=EventType.RECEIVE_BLOCK, peer_id=neighbor_id, block=block, from_peer=self.peer_id)
                        network.schedule_event(event_queue, event)

    def validate_block(self, block):
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
            if sender == "0":
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
        chain = []
        current_block = block
        while current_block:
            chain.append(current_block)
            prev_block_id = current_block.prev_block_id
            current_block = self.blockchain.get(prev_block_id, None)
        chain.reverse()
        return chain

    def construct_chain_by_id(self, block_id):
        chain = []
        current_block = self.blockchain.get(block_id, None)
        while current_block:
            chain.insert(0, current_block)
            prev_block_id = current_block.prev_block_id
            current_block = self.blockchain.get(prev_block_id, None)
        return chain

    def update_blockchain(self, new_block):
        chain = self.construct_chain(new_block)
        self.current_longest_chain = copy.deepcopy(chain)
        self.recompute_balances()

    def calculate_balance(self):
        return self.current_balances.get(self.peer_id, INITIAL_BALANCE)

    # ----- Two-Step Block Propagation Methods -----

    def broadcast_block_hash(self, current_time, event_queue, network, block):
        """
        Broadcast only the block hash to neighbors.
        For honest nodes, broadcast to all peers.
        For malicious nodes, use the malicious overlay if applicable.
        """
        block_hash = block.block_id  # Block ID used as hash.
        self.known_hashes[block_hash] = block

        # Malicious node handling.
        if self.is_malicious:
            if self.is_ringmaster:
                for neighbor_id in self.connections:
                    if network.peers[neighbor_id].is_malicious:
                        delay = random.uniform(MALICIOUS_MIN_PROP_DELAY, MALICIOUS_MAX_PROP_DELAY)
                        event_time = current_time + delay
                        payload = {'hash': block_hash, 'from_peer': self.peer_id}
                        event = Event(time=event_time, event_type=EventType.RECEIVE_HASH, peer_id=neighbor_id, **payload)
                        network.schedule_event(event_queue, event)
                self.private_chain.append(block)
            else:
                self.private_chain.append(block)
            return

        # Honest node broadcasting: send hash message to all neighbors.
        for neighbor_id in self.connections:
            delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': HASH_SIZE}))
            event_time = current_time + delay
            payload = {'hash': block_hash, 'from_peer': self.peer_id}
            event = Event(time=event_time, event_type=EventType.RECEIVE_HASH, peer_id=neighbor_id, **payload)
            network.schedule_event(event_queue, event)

    def receive_hash(self, current_time, event_queue, network, block_hash, from_peer, Tt):
        """
        When a node receives a block hash, if it doesn't have the full block,
        initiate a GET request after starting a timer.
        """
        if block_hash in self.known_hashes:
            return  # Full block already known.
        if block_hash not in self.pending_hash_requests:
            self.pending_hash_requests[block_hash] = {
                'timer': current_time + Tt,
                'requested_from': [from_peer]
            }
            self.send_get_request(current_time, event_queue, network, block_hash, from_peer, Tt)
        else:
            if from_peer not in self.pending_hash_requests[block_hash]['requested_from']:
                self.pending_hash_requests[block_hash]['requested_from'].append(from_peer)

    def send_get_request(self, current_time, event_queue, network, block_hash, target_peer, Tt):
        """
        Send a GET request for the full block.
        """
        delay = network.calculate_latency(self.peer_id, target_peer, type('Msg', (), {'size': HASH_SIZE}))
        event_time = current_time + delay
        payload = {'hash': block_hash, 'from_peer': self.peer_id}
        event = Event(time=event_time, event_type=EventType.GET_REQUEST, peer_id=target_peer, **payload)
        network.schedule_event(event_queue, event)
        timeout_event = Event(time=current_time + Tt, event_type=EventType.TIMEOUT_EVENT, peer_id=self.peer_id, hash=block_hash)
        network.schedule_event(event_queue, timeout_event)

    def handle_get_request(self, current_time, event_queue, network, block_hash, from_peer):
        """
        When a GET request is received, send the full block if available.
        Malicious nodes may withhold honest block data per the Eclipse attack.
        """
        if block_hash not in self.known_hashes:
            return
        block = self.known_hashes[block_hash]
        if self.is_malicious:
            # For honest blocks, malicious nodes withhold the full block to launch an eclipse attack.
            if not network.peers[block.miner_id].is_malicious:
                print(f"Malicious Peer {self.peer_id} withholding honest block {block.block_id[:6]} at time {current_time:.2f}")
                return
        delay = network.calculate_latency(self.peer_id, from_peer, type('Msg', (), {'size': MAX_BLOCK_SIZE}))
        event_time = current_time + delay
        payload = {'block': block, 'from_peer': self.peer_id}
        event = Event(time=event_time, event_type=EventType.BLOCK_RESPONSE, peer_id=from_peer, **payload)
        network.schedule_event(event_queue, event)

    def receive_block_response(self, current_time, event_queue, network, block, Tt):
        """
        Upon receiving a full block response, store it and update blockchain if necessary.
        """
        block_hash = block.block_id
        self.known_hashes[block_hash] = block
        if block_hash in self.pending_hash_requests:
            del self.pending_hash_requests[block_hash]
        candidate_chain = self.construct_chain(block)
        if len(candidate_chain) > len(self.current_longest_chain):
            self.blockchain[block.block_id] = block
            self.update_blockchain(block)
            print(f"Peer {self.peer_id} updated chain via BLOCK_RESPONSE at time {current_time:.2f}")
            if not self.is_malicious:
                self.broadcast_block_hash(current_time, event_queue, network, block)

    def handle_timeout(self, current_time, event_queue, network, block_hash, Tt):
        """
        If timeout expires and the full block has not been received, resend GET request.
        """
        if block_hash in self.known_hashes:
            return
        if block_hash in self.pending_hash_requests:
            pending = self.pending_hash_requests[block_hash]
            if current_time >= pending['timer']:
                target_peer = pending['requested_from'][0]
                self.send_get_request(current_time, event_queue, network, block_hash, target_peer, Tt)
                pending['timer'] = current_time + Tt
