# config.py

# Simulation parameters
NUM_PEERS = 50  # Adjusted number of peers for testing
PERCENT_SLOW = 0.5  # Percentage of slow nodes
PERCENT_LOW_CPU = 0.5  # Percentage of low CPU nodes
MEAN_TX_INTERVAL = 5  # Mean time between transactions (increase transaction rate)
MEAN_BLOCK_INTERVAL = 15 # Decreased block interval for higher mining rate
SIMULATION_TIME = 600  # Total simulation time in seconds (adjusted for testing)

# Network parameters
MIN_CONNECTIONS = 3
MAX_CONNECTIONS = 6

MIN_PROP_DELAY = 2.0  # Increased minimum propagation delay
MAX_PROP_DELAY = 10.0  # Increased maximum propagation delay

FAST_LINK_SPEED = 100e6  # 100 Mbps
SLOW_LINK_SPEED = 5e6    # 5 Mbps

TRANSACTION_SIZE = 1 * 1024  # Transaction size in bytes (1 KB)
MAX_BLOCK_SIZE = 1 * 1024 * 1024  # Max block size in bytes (1 MB)
EMPTY_BLOCK_SIZE = 1 * 1024  # Size of an empty block (1 KB)
COINBASE_AMOUNT = 50  # Mining reward

# Other parameters
INITIAL_BALANCE = 1000  # Starting balance for each peer
