from typing import List
import numpy as np
from block import Block
from event import EventType
from event_queue import EventQueue
from simulator_parameters import SimulatorParameters
from transaction import Transaction


class Simulator:
    def __init__(self, sp: SimulatorParameters):
        self.simulator_parameters: SimulatorParameters = sp
        self.global_time: float = 0.0
        self.event_queue: EventQueue = EventQueue()
        self.freeze_everything_except_network: bool = False
        pass

    def initialize(self) -> None:
        global g_logger, hash_power_median

        # self.genesis_block = self.__create_genesis_block()
        self.genesis_block = self.__create_genesis_block_v2_empty()
        list_slow_fast: List[bool] = ([False] * self.simulator_parameters.number_of_slow_nodes) \
                                     + ([True] * self.simulator_parameters.number_of_fast_nodes)
        np.random.shuffle(list_slow_fast)

        list_malicious: List[bool] = [
            i < self.simulator_parameters.number_of_malicious_nodes
            for i in range(self.simulator_parameters.n_total_nodes)
        ]
        np.random.shuffle(list_malicious)
        debug_malicious_idx: List[int] = list()
        for i in range(self.simulator_parameters.n_total_nodes):
            if list_malicious[i]:
                debug_malicious_idx.append(i)
        g_logger.debug(f'{debug_malicious_idx=}')

        # Point 7 of PDF: Randomly generate CPU power of the nodes
        hash_power_percent: List[float] = list(np.random.random(self.simulator_parameters.n_total_nodes))
        hash_power_percent_sum = 100 / sum(hash_power_percent)
        hash_power_percent = [i * hash_power_percent_sum for i in hash_power_percent]
        hash_power_median = np.median(hash_power_percent)

        g_logger.debug(f'{hash_power_percent=}')

        self.params = zip(hash_power_percent, list_slow_fast, list_malicious)
 
        pass

    # REFER: https://www.geeksforgeeks.org/private-methods-in-python/
    def __create_genesis_block_v1(self) -> 'Block':
        """This method shall only be called during the start of the simulation"""
        min_of_block_limit_and_nodes = min(self.simulator_parameters.n_total_nodes,
                                           self.simulator_parameters.max_transactions_per_block)

        # REFER: https://np.org/doc/stable/reference/random/generated/np.random.randint.html#np.random.randint
        # “discrete uniform” distribution

        # Uniform random distribution to nodes
        recv_node_idx = np.random.randint(
            low=0,
            high=self.simulator_parameters.n_total_nodes,
            size=min_of_block_limit_and_nodes
        )

        # Uniform random distribution of money
        # In real life, these coins will be with people instead of nodes
        # TODO: change to np.random.uniform to generate float value for initial coins a node has
        money = np.random.randint(
            low=self.simulator_parameters.node_initial_coins_low,
            high=self.simulator_parameters.node_initial_coins_high + 1,
            size=min_of_block_limit_and_nodes
        )

        # Sender = -1 denotes that coins are created from thin air in the genesis block
        transactions = [Transaction(0.0, -1, recv_idx, coins) for recv_idx, coins in zip(recv_node_idx, money)]
        return Block('-1', 0.0, 0, transactions, 0.0, 0.0)

    def __create_genesis_block_v2_empty(self) -> 'Block':
        """This method shall only be called during the start of the simulation"""
        return Block('-1', 0.0, 0, list(), 0.0, 0.0)

    def freeze(self) -> None:
        self.freeze_everything_except_network = True
        # self.event_queue.freeze()

    def execute_next_event(self, execute_all_same_time_events: bool = True) -> bool:
        """This will execute all events with event_completion_time==queue.top().event_completion_time"""
        global g_logger
        if self.event_queue.empty():
            g_logger.debug(f'Event queue is empty, returning...')
            return False

        event = self.event_queue.pop()
        while True:
            self.global_time = event.event_completion_time
            # NOTE: the "if" condition is used to reduce the number of redundant log operations
            if self.freeze_everything_except_network:
                if event.event_type in [EventType.EVENT_TRANSACTION_CREATE, EventType.EVENT_BLOCK_CREATE_SUCCESS]:
                    g_logger.debug(f'FREEZED: Time={self.get_global_time():.5f} , Event = {event.str_all()}')
                    break
                elif event.event_type not in [EventType.EVENT_TRANSACTION_CREATE, EventType.EVENT_RECV_TRANSACTION]:
                    g_logger.debug(f'Network: Time={self.get_global_time():.5f} , Event = {event.str_all()}')
            elif event.event_type not in [EventType.EVENT_TRANSACTION_CREATE, EventType.EVENT_RECV_TRANSACTION]:
                # NOTE: EventType.EVENT_RECV_TRANSACTION are not logged because they create a
                #       lot of log statements (as they are the most highly performed operations)
                #       and are of no use during debugging
                g_logger.debug(f'Time={self.get_global_time():.5f} , Event = {event.str_all()}')

            if event.event_type == EventType.EVENT_TRANSACTION_CREATE:
                txn: Transaction = event.data_obj
                self.nodes_list[event.event_receiver_id].transaction_event_handler(txn)
            elif event.event_type == EventType.EVENT_RECV_TRANSACTION:
                txn: Transaction = event.data_obj
                self.nodes_list[event.event_receiver_id].transaction_recv(txn, event.event_creator_id)
            elif event.event_type == EventType.EVENT_RECV_BLOCK:
                blk: Block = event.data_obj
                self.nodes_list[event.event_receiver_id].block_recv(blk, event.event_creator_id, self.global_time)
            elif event.event_type == EventType.EVENT_BLOCK_CREATE_SUCCESS:
                blk: Block = event.data_obj
                self.nodes_list[event.event_receiver_id].mining_complete(blk)
            else:
                g_logger.error(f'Problem: Unexpected EventType={event.event_type} , {event=}')

            if execute_all_same_time_events == False or \
                    self.event_queue.empty() or \
                    self.event_queue.top().event_completion_time > self.global_time:
                break
            event = self.event_queue.pop()
        return True

    def get_global_time(self) -> float:
        return self.global_time

    