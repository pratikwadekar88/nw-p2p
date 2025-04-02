# Simulation parameters
NUM_PEERS = 40                # Total number of peers in the network
PERCENT_SLOW = 1.0            # Honest nodes are slow (forced slow)
PERCENT_MALICIOUS = 0.5       # 30% of nodes are malicious (these are forced fast)

MEAN_TX_INTERVAL = 5          # Mean time between transactions (seconds)
MEAN_BLOCK_INTERVAL = 20      # Mean time between blocks (seconds)
SIMULATION_TIME = 1000       # Total simulation time in seconds

# Network parameters
MIN_CONNECTIONS = 3           # Minimum connections per node (normal network)
MAX_CONNECTIONS = 6           # Maximum connections per node (normal network)
MIN_PROP_DELAY = 0.01         # Minimum propagation delay in seconds (normal network)
MAX_PROP_DELAY = 0.5          # Maximum propagation delay in seconds (normal network)

FAST_LINK_SPEED = 100e6       # 100 Mbps (for malicious-fast nodes and overlay links)
SLOW_LINK_SPEED = 5e6         # 5 Mbps (for honest nodes)

# Block and Transaction parameters
TRANSACTION_SIZE = 1 * 1024   # Transaction size in bytes (1 KB)
MAX_BLOCK_SIZE = 1 * 1024 * 1024  # Maximum block size in bytes (1 MB)
EMPTY_BLOCK_SIZE = 1 * 1024   # Size of an empty block in bytes (1 KB)
COINBASE_AMOUNT = 50          # Reward for mining a block
INITIAL_BALANCE = 1000        # Starting balance for each peer

# Attack-related parameters
ECLIPSE_ATTACK_ENABLED = True  # Enable or disable the eclipse attack mechanism
SELFISH_MINING_ENABLED = True   # Enable or disable the selfish mining strategy

# Timeout parameter for GET requests (in seconds)
DATA_REQUEST_TIMEOUT = 5
