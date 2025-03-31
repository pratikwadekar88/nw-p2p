# config.py

# Simulation parameters
NUM_PEERS = 100                   # Total number of peers
PERCENT_SLOW = 0.5               # Percentage of slow nodes (honest nodes are slow)
PERCENT_LOW_CPU = 0.5            # Percentage of low CPU nodes (honest nodes are low CPU)
MEAN_TX_INTERVAL = 5             # Mean time between transactions (seconds)
MEAN_BLOCK_INTERVAL = 20         # Mean block interval (seconds)
SIMULATION_TIME = 5000          # Total simulation time (seconds)

# Network parameters
MIN_CONNECTIONS = 3
MAX_CONNECTIONS = 6

MIN_PROP_DELAY = 0.01            # Minimum propagation delay (seconds)
MAX_PROP_DELAY = 0.5             # Maximum propagation delay (seconds)

FAST_LINK_SPEED = 100e6          # 100 Mbps
SLOW_LINK_SPEED = 5e6            # 5 Mbps

# Entity sizes
TRANSACTION_SIZE = 1 * 1024      # 1 KB per transaction
MAX_BLOCK_SIZE = 1 * 1024 * 1024  # 1 MB max block size
EMPTY_BLOCK_SIZE = 1 * 1024       # 1 KB empty block (header only)
COINBASE_AMOUNT = 50             # Coinbase reward

# Other parameters
INITIAL_BALANCE = 1000           # Starting balance for each peer

# Enhanced propagation & attack parameters
TIMEOUT_TT = 1                   # Timeout (seconds) for waiting full block data
PERCENT_MALICIOUS = 0.30         # Fraction of nodes that are malicious (30%)
