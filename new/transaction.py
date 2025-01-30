import hashlib

class Transaction:
    def __init__(self, tx_time: float, id_sender: int, id_receiver: int, tx_amt: float):
        self.tx_time: float = tx_time
        self.id_sender: int = id_sender
        self.id_receiver: int = id_receiver
        self.tx_amt: float = tx_amt
        # Note: this is not used much in this simulator. However, it is very useful in real life
        self.tx_hash: str = self.get_hash()

    def __str__(self) -> str:
        return str([self.tx_time, self.id_sender, self.id_receiver, self.tx_amt])

    def __eq__(self, other) -> bool:
        return type(self) == type(other) and self.tx_hash == other.tx_hash

    def __hash__(self):
        return int(self.get_hash(), base=16)

    def get_hash(self) -> str:
        return hashlib.md5(str(self).encode()).hexdigest()

    @staticmethod
    def size() -> int:
        """
        Returns size in Bytes
        NOTE: Size is assumed to be 1KB (According to the Problem Statement PDF)
        """
        return 1000