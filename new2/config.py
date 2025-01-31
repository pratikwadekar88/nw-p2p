# config.py

# Simulation parameters
NUM_PEERS = 10  # Number of peers (n)
PERCENT_SLOW = 0.3  # Percentage of slow nodes (z0)
PERCENT_LOW_CPU = 0.4  # Percentage of low CPU nodes (z1)
MEAN_TX_INTERVAL = 10  # Mean time between transactions (T_tx)
MEAN_BLOCK_INTERVAL = 600  # Average interarrival time between blocks (I)
SIMULATION_TIME = 3600  # Total simulation time in seconds

# Network parameters
MIN_CONNECTIONS = 3
MAX_CONNECTIONS = 6

MIN_PROP_DELAY = 0.01  # Minimum propagation delay (ρ), in seconds
MAX_PROP_DELAY = 0.5   # Maximum propagation delay (ρ), in seconds

FAST_LINK_SPEED = 100e6  # 100 Mbps
SLOW_LINK_SPEED = 5e6    # 5 Mbps

TRANSACTION_SIZE = 1 * 1024  # Transaction size in bytes (1 KB)
MAX_BLOCK_SIZE = 1 * 1024 * 1024  # Max block size in bytes (1 MB)
EMPTY_BLOCK_SIZE = 1 * 1024  # Size of an empty block (1 KB)
COINBASE_AMOUNT = 50  # Mining reward

# Other parameters
INITIAL_BALANCE = 1000  # Starting balance for each peer
