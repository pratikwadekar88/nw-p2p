# Configuration file for simulation parameters and constants

# Simulation parameters (can be overridden via command-line arguments)
SIM_PARAMS = {
    "n_peers": 20,  # Total number of peers in the network
    "z0_slow_percent": 20,  # Percentage of slow peers
    "z1_low_cpu_percent": 30,  # Percentage of low CPU peers
    "mean_tx_interval": 10,  # Mean time between transactions (Ttx)
    "block_interval": 600,  # Mean time between blocks (I)
    "simulation_time": 3600,  # Total simulation time in seconds
    "initial_coins": 1000  # Initial coins for each peer
}

# Network constants
GENESIS_BLOCK_ID = "0" * 64  # ID for the genesis block
MAX_BLOCK_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB block size limit
COINBASE_REWARD = 50  # Mining reward
TX_SIZE = 1024  # 1 KB per transaction
BLOCK_INTERVAL = 600  # 10 minutes between blocks
INITIAL_COINS = 1000  # Initial coins for each peer
current_time = 0
# Network parameters
SLOW_LINK_SPEED = 5e6  # 5 Mbps for slow links
FAST_LINK_SPEED = 100e6  # 100 Mbps for fast links
MIN_PROPAGATION_DELAY = 0.01  # 10ms minimum propagation delay
MAX_PROPAGATION_DELAY = 0.5  # 500ms maximum propagation delay

def update_config(args):
    """Update simulation parameters from command-line arguments."""
    SIM_PARAMS.update(vars(args))