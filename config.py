import argparse

# Default simulation parameters
SIM_PARAMS = {
    "n_peers": 20,
    "z0_slow_percent": 20,
    "z1_low_cpu_percent": 30,
    "mean_tx_interval": 10,
    "block_interval": 600,
    "simulation_time": 3600,
    "initial_coins": 1000
}

# Network constants
GENESIS_BLOCK_ID = "0" * 64
MAX_BLOCK_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB
COINBASE_REWARD = 50
TX_SIZE = 1024  # 1 KB

# Network parameters
SLOW_LINK_SPEED = 5e6      # 5 Mbps
FAST_LINK_SPEED = 100e6    # 100 Mbps
MIN_PROPAGATION_DELAY = 0.01  # 10ms
MAX_PROPAGATION_DELAY = 0.5   # 500ms

def update_config(args):
    SIM_PARAMS.update(vars(args))