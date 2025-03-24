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
        self.connections = []             # list of peer IDs in honest chain
        self.pending_transactions = {}    # txn_id -> Transaction
        self.received_transactions = set()
        self.blockchain = {}              # block_id -> Block
        self.current_longest_chain = []   # list of Blocks (the main chain)
        self.current_balances = {}
        self.hash_power = None # the hash fraction of peer wrt total hashing power of network

        # Fields for enhanced propagation (two-step block delivery)
        self.known_hashes = {}            # block_hash -> Block (if full block already received)
        self.pending_hash_requests = {}   # block_hash -> { 'timer': float, 'requested_from': [peer_ids] }
        
        # Fields for selfish mining & eclipse attack simulation.
        self.is_malicious = False         # default honest; set in Simulation.setup()
        self.is_ringmaster = False        # for malicious ringmaster only
        # self.private_chain = []
        self.private_connections = []           # list of peer IDs in private chain


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
                    event = Event(time=event_time, event_type=EventType.RECEIVE_TRANSACTION, peer_id=neighbor_id, transaction=txn, from_peer=self.peer_id)
                    event_queue.schedule_event(event)
        interarrival_time = random.expovariate(1 / MEAN_TX_INTERVAL)
        next_event_time = current_time + interarrival_time
        if next_event_time <= SIMULATION_TIME:
            next_event = Event(time=next_event_time, event_type=EventType.GENERATE_TRANSACTION, peer_id=self.peer_id)
            event_queue.schedule_event(next_event)


    def receive_transaction(self, transaction, from_peer, current_time, event_queue, network):
        if transaction.txn_id not in self.received_transactions:
            self.received_transactions.add(transaction.txn_id)
            self.pending_transactions[transaction.txn_id] = transaction
            for neighbor_id in self.connections:
                if neighbor_id != from_peer:
                    delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': TRANSACTION_SIZE}))
                    event_time = current_time + delay
                    if event_time <= SIMULATION_TIME:
                        event = Event(time=event_time, event_type=EventType.RECEIVE_TRANSACTION, peer_id=neighbor_id, transaction=transaction, from_peer=self.peer_id)
                        event_queue.schedule_event(event)


    def schedule_block_mined(self, current_time, event_queue):
        if (self.hash_power == 0): # Malicious blocks except ringmaster have hash power of 0. Ringmaster has all of their hashing power.
            return;
    
        mean_time = MEAN_BLOCK_INTERVAL / self.hash_power
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
            block_size += TRANSACTION_SIZE  # Add size of coinbase transaction

            block = Block(miner_id=self.peer_id, prev_block_id=prev_block_id, transactions=transactions, timestamp=current_time)
            event = Event(time=event_time, event_type=EventType.BLOCK_MINED, peer_id=self.peer_id, block=block)
            event_queue.schedule_event(event)


    # Handles the event when a block is mined by the peer.
    def block_mined(self, current_time, event_queue, network, block):
        # check if the chain length is same still
        candidate_chain = self.construct_chain(block)

        # Compare chain lengths
        current_chain_length = len(self.current_longest_chain)
        candidate_chain_length = len(candidate_chain)

        if (candidate_chain_length <= current_chain_length):
            for txn in block.transactions:
                self.pending_transactions[txn.txn_id] = txn
            print(f"Peer {self.peer_id} rejected block {block.block_id[:6]} at time {current_time:.2f} (chain too short)")
            # drop this block, since another block has already been mined, hence this block mined event is discarded 
        else:
            # Add block to blockchain
            self.blockchain[block.block_id] = block

            # Update longest chain
            self.update_blockchain(block)
            print(f"Peer {self.peer_id} mined block {block.block_id[:6]} at time {current_time:.2f}")

            # broadcast block hash to neighbors
            block_hash = block.block_id  # Block ID used as hash.
            self.known_hashes[block_hash] = block

            # if ringmaster mines the block, that block is immediately broadcasted to whole malicious overlay network only
            # otherwise broadcast it to all the neighboring miners
            if self.is_ringmaster:
                broadcasting_connections = self.private_connections
                on_overlay = True; # whether this event happened via regular network or the overlay network
            else:
                broadcasting_connections = self.connections
                on_overlay = False;

            for neighbor_id in broadcasting_connections:
                # if we are malicious and target peer is malicious, this will  use overlay network
                delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': HASH_SIZE})) # creates a new class named Msg, containing an attibute 'size'
                event_time = current_time + delay
                if (event_time > SIMULATION_TIME): # dont schedule the event if its time exceeds the simulation time
                    continue;
                payload = {'hash': block_hash, 'from_peer': self.peer_id, 'overlay': on_overlay}
                event = Event(time=event_time, event_type=EventType.RECEIVE_HASH, peer_id=neighbor_id, **payload)
                event_queue.schedule_event(event)

            # Start mining next block
            self.schedule_block_mined(current_time, event_queue)



    # def block_mined(self, current_time, event_queue, network, block):
    #     """
    #     Revised block_mined function with detailed tie-breaker logic.
    #     """
    #     candidate_chain = self.construct_chain(block)
    #     current_chain_length = len(self.current_longest_chain)
    #     candidate_chain_length = len(candidate_chain)
        
    #     if candidate_chain_length < current_chain_length:
    #         # Block did not extend the chain; requeue its transactions.
    #         for txn in block.transactions:
    #             self.pending_transactions[txn.txn_id] = txn
    #         print(f"Peer {self.peer_id} rejected block {block.block_id[:6]} at time {current_time:.2f} (chain too short)")
        
    #     elif candidate_chain_length == current_chain_length:
    #         # Equal-length chain, tie-breaker.
    #         if random.choice([True, False]):
    #             self.blockchain[block.block_id] = block
    #             self.update_blockchain(block)
    #             print(f"Peer {self.peer_id} switched to an equal-length chain with block {block.block_id[:6]} at time {current_time:.2f}")
    #             self.broadcast_block_hash(current_time, event_queue, network, block)
    #         else:
    #             for txn in block.transactions:
    #                 self.pending_transactions[txn.txn_id] = txn
    #             print(f"Peer {self.peer_id} ignored equal-length block {block.block_id[:6]} at time {current_time:.2f}")
        
    #     else:  # candidate_chain_length > current_chain_length
    #         self.blockchain[block.block_id] = block
    #         self.update_blockchain(block)
    #         print(f"Peer {self.peer_id} extended chain with block {block.block_id[:6]} at time {current_time:.2f}")
    #         self.broadcast_block_hash(current_time, event_queue, network, block)
        
    #     # Always schedule new mining event for continuous block creation.
    #     self.schedule_block_mined(current_time, event_queue, network)



    # check if hash is received from regular network or overlay network
    def receive_hash(self, current_time, event_queue, network, block_hash, from_peer, on_overlay, Tt):
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
            self.send_get_request(current_time, event_queue, network, block_hash, from_peer, on_overlay, Tt)
        else: # already have hash, waiting for actual block
            if from_peer not in self.pending_hash_requests[block_hash]['requested_from']:
                self.pending_hash_requests[block_hash]['requested_from'].append(from_peer)



    def send_get_request(self, current_time, event_queue, network, block_hash, target_peer, on_overlay, Tt):
        # Send a GET request for the full block.
        # if we are malicious and target peer is malicious, then send this request was actually using overlay network
        delay = network.calculate_latency(self.peer_id, target_peer, type('Msg', (), {'size': HASH_SIZE}))
        event_time = current_time + delay            
        if (event_time > SIMULATION_TIME):
            return;
        payload = {'hash': block_hash, 'from_peer': self.peer_id, 'overlay': on_overlay}
        event = Event(time=event_time, event_type=EventType.GET_REQUEST, peer_id=target_peer, **payload)
        event_queue.schedule_event(event)
        timeout_event = Event(time=current_time + Tt, event_type=EventType.TIMEOUT_EVENT, peer_id=self.peer_id, **payload)
        event_queue.schedule_event(timeout_event)


    def handle_get_request(self, current_time, event_queue, network, block_hash, from_peer, on_overlay):
        """
        When a GET request is received, send the full block if available.
        Malicious nodes may withhold honest block data per the Eclipse attack.
        """
        # if the request is received on overlay network, send the block, otherwise not
        if block_hash not in self.known_hashes:
            return
        
        block = self.known_hashes[block_hash]

        # if get request received on regular network, withhold the block
        if self.is_malicious and not on_overlay:
            print(f"Malicious Peer {self.peer_id} withholding honest block {block.block_id[:6]} at time {current_time:.2f}")
            return
        
        # otherwise send the block if request was received on overlay network
        # or if you are honest
        delay = network.calculate_latency(self.peer_id, from_peer, type('Msg', (), {'size': MAX_BLOCK_SIZE}))
        event_time = current_time + delay
        if (event_time > SIMULATION_TIME):
            return
        
        payload = {'block': block, 'from_peer': self.peer_id, 'overlay': on_overlay}
        event = Event(time=event_time, event_type=EventType.RECEIVE_BLOCK, peer_id=from_peer, **payload)
        event_queue.schedule_event(event)


    # def receive_block(self, block, from_peer, current_time, event_queue, network):
    #     """
    #     Receives a block and updates the blockchain if valid.

    #     Args:
    #         block (Block): The received block.
    #         from_peer (str): ID of the peer from which the block was received.
    #         current_time (float): Current simulation time.
    #         event_queue (list): Event queue.
    #         network (Network): Network object.
    #     """
    #     if block.block_id not in self.blockchain:
    #         # Validate block
    #         if self.validate_block(block):
    #             self.blockchain[block.block_id] = block

    #             # Remove transactions included in the block from pending_transactions
    #             for txn in block.transactions:
    #                 self.pending_transactions.pop(txn.txn_id, None)

    #             # Construct candidate chain
    #             candidate_chain = self.construct_chain(block)

    #             # Compare chain lengths
    #             current_chain_length = len(self.current_longest_chain)
    #             candidate_chain_length = len(candidate_chain)

    #             if candidate_chain_length > current_chain_length:
    #                 self.update_blockchain(block)
    #                 print(f"Peer {self.peer_id} switched to a longer chain at time {current_time:.2f}")
    #                 self.schedule_block_mined(current_time, event_queue, network) # start mining the new block from now
    #             elif candidate_chain_length == current_chain_length:
    #                 # Random tie-breaker
    #                 if random.choice([True, False]):
    #                     self.update_blockchain(block)
    #                     print(f"Peer {self.peer_id} switched to an equal-length chain at time {current_time:.2f}")
    #                     self.schedule_block_mined(current_time, event_queue, network)

    #             # Forward block to neighbors except the one it came from
    #             for neighbor_id in self.connections:
    #                 if neighbor_id != from_peer:
    #                     delay = network.calculate_latency(self.peer_id, neighbor_id, block)
    #                     event_time = current_time + delay
    #                     if event_time <= SIMULATION_TIME:
    #                         event = Event(
    #                             time=event_time,
    #                             event_type=EventType.RECEIVE_BLOCK,
    #                             peer_id=neighbor_id,
    #                             block=block,
    #                             from_peer=self.peer_id
    #                         )
    #                         network.schedule_event(event_queue, event)


    def receive_block(self, current_time, event_queue, network, block, from_peer, on_overlay, Tt):
        """
        Upon receiving a full block response, validate it and update blockchain if correct.
        Then broadcast its hash further
        """

        block_hash = block.block_id
        if block_hash in self.pending_hash_requests:
            del self.pending_hash_requests[block_hash]
        else:
            return # we were not waiting for this block

        if block.block_id not in self.blockchain:
            # Validate block
            if self.validate_block(block):
                self.blockchain[block.block_id] = block
                self.known_hashes[block_hash] = block

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
                    self.schedule_block_mined(current_time, event_queue) # start mining the new block from now
                elif candidate_chain_length == current_chain_length:
                    # Random tie-breaker
                    if random.choice([True, False]):
                        self.update_blockchain(block)
                        print(f"Peer {self.peer_id} switched to an equal-length chain at time {current_time:.2f}")
                        self.schedule_block_mined(current_time, event_queue)

                # Forward block hash to neighbors except the one it came from
                if on_overlay:
                    broadcasting_connections = self.private_connections
                    on_overlay = True; # whether this event happened via regular network or the overlay network
                else:
                    broadcasting_connections = self.connections
                    on_overlay = False;

                for neighbor_id in broadcasting_connections:
                    if neighbor_id == from_peer:
                        continue;
                    delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': HASH_SIZE})) # creates a new class named Msg, containing an attibute 'size'
                    event_time = current_time + delay
                    if (event_time > SIMULATION_TIME): # dont schedule the event if its time exceeds the simulation time
                        continue;
                    payload = {'hash': block_hash, 'from_peer': self.peer_id, 'overlay': on_overlay}
                    event = Event(time=event_time, event_type=EventType.RECEIVE_HASH, peer_id=neighbor_id, **payload)
                    event_queue.schedule_event(event)




    def handle_timeout(self, current_time, event_queue, network, block_hash, from_peer, on_overlay, Tt):
        """
        If timeout expires and the full block has not been received, resend GET request.
        """
        if block_hash in self.known_hashes:
            return
        if block_hash in self.pending_hash_requests:
            pending = self.pending_hash_requests[block_hash]

            # if timeout has been reached for this peer, try sending this request to next peer who sent you this hash
            if current_time >= pending['timer']:
                if len(pending['requested_from']) > 1:
                    pending['requested_from'] = pending['requested_from'][1:]
                target_peer = pending['requested_from'][0]
                self.send_get_request(current_time, event_queue, network, block_hash, target_peer, on_overlay, Tt)
                pending['timer'] = current_time + Tt



    def validate_block(self, block):
        """
        Validates a block by checking its transactions and previous block.

        Args:
            block (Block): The block to be validated.

        Returns:
            bool: True if the block is valid, False otherwise.
        """
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
    


    def construct_chain(self, block):
        """
        Constructs the chain leading to a given block.

        Args:
            block (Block): The block to construct the chain for.

        Returns:
            list: List of blocks in the chain.
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
        Constructs the chain up to a given block ID (used in validation).

        Args:
            block_id (str): The block ID to construct the chain for.

        Returns:
            list: List of blocks in the chain.
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
        Updates the blockchain with a new block.

        Args:
            new_block (Block): The new block to be added.
        """
        chain = self.construct_chain(new_block)
        self.current_longest_chain = copy.deepcopy(chain)
        self.recompute_balances()


    def calculate_balance(self):
        """
        Calculates the peer's current balance.

        Returns:
            float: The current balance of the peer.
        """
        return self.current_balances.get(self.peer_id, INITIAL_BALANCE)




    # ----- Two-Step Block Propagation Methods -----

    # def broadcast_block_hash(self, current_time, event_queue, network, block):
    #     """
    #     Broadcast only the block hash to neighbors.
    #     For honest nodes, broadcast to all peers.
    #     For malicious nodes, use the malicious overlay if applicable.
    #     """
    #     block_hash = block.block_id  # Block ID used as hash.
    #     self.known_hashes[block_hash] = block

    #     # Malicious node handling.
    #     if self.is_malicious:
    #         if self.is_ringmaster:
    #             for neighbor_id in self.connections:
    #                 if network.peers[neighbor_id].is_malicious:
    #                     delay = random.uniform(MALICIOUS_MIN_PROP_DELAY, MALICIOUS_MAX_PROP_DELAY)
    #                     event_time = current_time + delay
    #                     payload = {'hash': block_hash, 'from_peer': self.peer_id}
    #                     event = Event(time=event_time, event_type=EventType.RECEIVE_HASH, peer_id=neighbor_id, **payload)
    #                     network.schedule_event(event_queue, event)
    #             self.private_chain.append(block)
    #         else:
    #             self.private_chain.append(block)
    #         return

    #     # Honest node broadcasting: send hash message to all neighbors.
    #     for neighbor_id in self.connections:
    #         delay = network.calculate_latency(self.peer_id, neighbor_id, type('Msg', (), {'size': HASH_SIZE}))
    #         event_time = current_time + delay
    #         payload = {'hash': block_hash, 'from_peer': self.peer_id}
    #         event = Event(time=event_time, event_type=EventType.RECEIVE_HASH, peer_id=neighbor_id, **payload)
    #         network.schedule_event(event_queue, event)

