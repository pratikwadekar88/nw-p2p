import time
import argparse
import json
import os
from config import SIM_PARAMS, update_config
from event import Event, EventQueue
from peer import Peer
from network import create_network

import random
event_queue = EventQueue()
current_time = 0
def main():
    parse_arguments()
    peers = create_peers()
    create_network(peers)
    schedule_initial_events(peers)
    run_simulation()
    save_results(peers)

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_peers", type=int)
    parser.add_argument("--z0", type=float)
    parser.add_argument("--z1", type=float)
    parser.add_argument("--sim_time", type=int)
    args = parser.parse_args()
    update_config(args)

def create_peers():
    peers = []
    total_hash_power = sum(10 if not p.is_low_cpu else 1 for p in peers)
    for i in range(SIM_PARAMS["n_peers"]):
        is_slow = random.random() < SIM_PARAMS["z0_slow_percent"] / 100
        is_low_cpu = random.random() < SIM_PARAMS["z1_low_cpu_percent"] / 100
        hash_power = 10 / total_hash_power if not is_low_cpu else 1 / total_hash_power
        peers.append(Peer(f"peer_{i}", is_slow, is_low_cpu, hash_power))
    return peers

# def schedule_initial_events(peers):
#     for peer in peers:
#         schedule_next_transaction(peer)
def schedule_initial_events(peers):
    for peer in peers:
        # Stagger initial mining events
        mining_delay = random.uniform(0, 5)  # Add small random delay
        event = Event(
            timestamp=mining_delay,
            event_type="start_mining",
            callback=peer.mine_block
        )
        event_queue.schedule(event)
        schedule_next_transaction(peer)

def schedule_next_transaction(peer):
    interval = random.expovariate(1 / SIM_PARAMS["mean_tx_interval"])
    # print(f"[DEBUG] Peer {peer.id} will generate a transaction in {interval:.2f}s")
    event = Event(
        timestamp=current_time + interval,
        event_type="generate_tx",
        callback=generate_transaction,
        data=peer
    )
    event_queue.schedule(event)

def generate_transaction(peer):
    
    receiver = random.choice([p for p in peer.neighbors])
    amount = random.randint(1, 100)
    tx = peer.generate_transaction(receiver.id, amount)
    # if(tx):
        # print(f"[DEBUG] Peer {peer.id} generated transaction {tx.id} to Peer {receiver.id}") # Done
    if tx:
        peer.receive_transaction(tx)
    schedule_next_transaction(peer)

def run_simulation():
    global current_time
    print(f"Running simulation for {SIM_PARAMS['simulation_time']} seconds...")
    while event_queue.queue and current_time < SIM_PARAMS["simulation_time"]:
        # print(f"\n[DEBUG] Current time: {current_time:.2f}s")
        event = event_queue.next_event()
        current_time = event.timestamp
        event.callback(event.data)


def save_results(peers):
    os.makedirs("blockchains", exist_ok=True)
    for peer in peers:
        with open(f"blockchains/{peer.id}.json", "w") as f:
            json.dump({
                "peer_id": peer.id,
                "chain": [{
                    "id": block.id,
                    "prev": block.prev_hash,
                    "miner": block.miner_id,
                    "txs": [tx.to_dict() for tx in block.transactions]
                } for block in peer.blockchain.chain]
            }, f)

if __name__ == "__main__":
    main()