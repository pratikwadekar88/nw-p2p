# config.py

# Simulation parameters
NUM_PEERS = 30  # Adjusted number of peers for testing
PERCENT_SLOW = 0.3  # Percentage of slow nodes
PERCENT_LOW_CPU = 0.3 # Percentage of low CPU nodes
MEAN_TX_INTERVAL = 5 # Mean time between transactions (increase transaction rate)
MEAN_BLOCK_INTERVAL = 50 # Decreased block interval for higher mining rate
SIMULATION_TIME = 1000  # Total simulation time in seconds (adjusted for testing)

# Network parameters
MIN_CONNECTIONS = 3
MAX_CONNECTIONS = 6

MIN_PROP_DELAY = 0.01  # Cannot be changed
MAX_PROP_DELAY = 0.5  # Cannot be changed

FAST_LINK_SPEED = 100e6  # 100 Mbps (Cannot be changed)
SLOW_LINK_SPEED = 5e6    # 5 Mbps (Cannot be changed)

TRANSACTION_SIZE = 1 * 1024  # Transaction size in bytes (1 KB)
MAX_BLOCK_SIZE = 1 * 1024 * 1024  # Max block size in bytes (1 MB)
EMPTY_BLOCK_SIZE = 1 * 1024  # Size of an empty block (only the header is present) (1 KB)
COINBASE_AMOUNT = 50  # Mining reward

# Other parameters
INITIAL_BALANCE = 1000  # Starting balance for each peer
