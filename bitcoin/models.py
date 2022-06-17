"""
Main implementation of the Bitcoin simulator.
"""

from sim.util import MAX_INCOMING_CONNECTIONS, MAX_OUTGOING_CONNECTIONS, SimpleAddress
import sys

from typing import Dict

sys.path.append("..")

from loguru import logger

from sim.base_models import *
from bitcoin.messages import *
from bitcoin.consensus import *
from bitcoin.bookkeeper import *


class Transaction(Item):
    def __init__(self, sender_id: str, created_at: int, size: float, value: float, fee: float):
        super().__init__(sender_id, 0)
        self.fee: Reward = fee
        self.size = 400  # bytes
        self.value = 100
        self.created_at = created_at
        self.feerate = self.fee / self.size

    def __str__(self) -> str:
        return f'TX (id:{self.id}, value: {self.value}, feerate: {self.feerate})'

    def __lt__(self, other):
        """
        Compare this Transaction object with another on the basis of their feerates.
        We want the mempool heap to treat the highest feerate as the "minimum" element, so the comparison operator is <=.
        """
        return self.feerate >= other.feerate


class BTCBlock(Block):
    def __init__(self, creator, prev_id: str, height: int):
        super().__init__(creator, prev_id, height)
        self.size = 80  # size of block header in bytes


class Miner(Node):
    """Represents a Bitcoin miner. """

    def __init__(self, name: str, mine_power: float, region: Region, iter_seconds, timestamp=0):
        """
        Create a Miner object.

        * name (str): Human-legible name for the miner. Uniqueness of names is not enforced.
        * mine_power (float): Mining power of the miner, representing what share of the global mining power this miner controls.
        * region (`sim.util.Region`): Miner's region.
        * iter_seconds (float): How many real-world seconds one simulation step corresponds to.
        * timestamp (int): Used to keep track of the simulation step count. Defaults to 0.
        """
        super().__init__(iter_seconds, name, region, timestamp)
        self.mine_power = mine_power
        self.max_block_size = 1
        self.tx_per_iter = 0

        # --- MODULES ---
        self.tx_model = None
        self.mine_strategy = None
        self.consensus_oracle: Oracle = None

        self.mempool: List[Transaction] = []  # heapq
        self.tx_ids: Dict[str, Transaction] = dict()

        # --- BOOKKEEPING ---
        self.bookkeeper: Bookkeeper = None

        logger.info(f'CREATED MINER {self.name}')

    def __getstate__(self):
        state = super().__getstate__()
        del state['mempool']
        del state['bookkeeper']
        return state

    def reset(self):
        """Reset state back to simulation start."""
        super().reset()
        self.mempool = []
        self.tx_ids = dict()
        self.bookkeeper.register_node(self)  # to reset stats

    def step(self, seconds: float):
        self.ping_peers()
        self.remove_stale_nodes()
        items = super().step(seconds)
        for item in items:
            self.consume(item)

        # TODO
        # tx_count = math.ceil(random.gauss(self.tx_per_iter, self.tx_per_iter / 10))
        tx_count = self.tx_per_iter
        for c in range(tx_count):
            self.tx_model.generate(self)

        if self.consensus_oracle.can_mine(self):
            self.mine_strategy.generate_block(self)

        # TODO: performance
        # space_use = sum([block.size for block in self.blockchain.values() if block != 'placeholder'])
        # space_use += self.tx_model.get_mempool_size(self)
        # self.bookkeeper.use_space(self, space_use)

    def ping_peers(self):
        for addr, node in self.outs.items():
            timestamp = self.tried_table.data[addr]['object'].timestamp
            if self.timestamp - timestamp > 20 * 60:
                self.send_to(node, PingMessage(self.id))

    def remove_stale_nodes(self):
        for node in self.outs.copy():
            timestamp = self.tried_table.data[node]['object'].timestamp
            if self.timestamp - timestamp > 40 * 60:
                self.outs.pop(node)

    def consume(self, item: Item):
        """
        Given an Item, performs the necessary action based on its type.
        * item (`sim.base_models.Item`): Item to consume.
        """
        if not self.is_online:
            return

        self.message_storage.add(item)

        snode = self.node_storage.get_node(item.sender_id)

        if snode and snode.id in self.tried_table.data and type(item) != VersionMessage:
            self.tried_table.update(snode.id, self.timestamp)

        if type(item) == BTCBlock:
            logger.info(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED BLOCK {item.id}')
            self.mine_strategy.receive_block(self, item, relay=True)
        elif type(item) == Transaction:
            self.tx_model.receive(self, item)
        elif type(item) == InvMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED INV MESSAGE FOR {item.type} {item.item_id}')
            if item.type == 'block':
                if self.blockchain.get(item.item_id, None) is None:
                    logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RESPONDED WITH GETDATA')
                    self.blockchain[item.item_id] = 'placeholder'  # not none
                    self.send_to(snode, GetDataMessage(item.item_id, item.type, self.id))
            elif item.type == 'tx':
                if self.tx_ids.get(item.item_id, None) is None:
                    logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RESPONDED WITH GETDATA')
                    self.tx_ids[item.item_id] = True
                    self.send_to(snode, GetDataMessage(item.item_id, item.type, self.id))
        elif type(item) == GetDataMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED GETDATA MESSAGE FOR {item.type} {item.item_id}')
            if item.type == 'block':
                try:
                    self.send_to(snode, self.blockchain[item.item_id])
                except KeyError:
                    pass
            elif item.type == 'tx':
                self.send_to(snode, self.tx_ids[item.item_id])
        elif type(item) == PingMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED PING MESSAGE FROM {item.sender_id}')
            self.send_to(snode, PongMessage(self.id))
        elif type(item) == PongMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED PONG MESSAGE FROM {item.sender_id}')
        elif type(item) == VersionMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED VERSION MESSAGE FROM {item.sender_id}')
            if len(self.ins) < MAX_INCOMING_CONNECTIONS:
                # this need to be changed since we cant provide the node itself
                self.ins[item.sender_id] = item.sender_node
                self.send_to(item.sender_node, VerAckMessage(self.id, self))
                logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> SENT VERACK MESSAGE TO {item.sender_id}')
        elif type(item) == VerAckMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECIEVED VERACK MESSAGE FROM {item.sender_id}')
            # if len(self.outs) < util.MAX_OUTGOING_CONNECTIONS
            self.outs[item.sender_id] = snode
            # snode.connect(self)
        elif type(item) == AddressMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECIEVED ADDRESS MESSAGE FROM {item.sender_id}')
            # if len(item.value) < 10:
            #     for node in random.choices(list(self.outs.values()), k=2):
            #         self.send_to(node, item)
            self.fill_new_table(item.sender_id, item.value)
        elif type(item) == GetAddrMessage:
            logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECIEVED GET ADDRESS MESSAGE FROM {item.sender_id}')
            addrs = self.tried_table.data.keys()
            self.send_to(snode, AddressMessage(self.id, addrs))

    def publish_item(self, item: Item, item_type: str):
        """
        Publishes an item over all of the node's outgoing connections.
        * item (`sim.base_models.Item`): Item to publish.
        * item_type (str): Item's type (e.g. 'block').
        """
        msg = InvMessage(item.id, item_type, self.id)
        for node in self.outs.values():
            self.send_to(node, msg)

    def print_blockchain(self, head: Block = None):
        head = self.mine_strategy.choose_head(self)
        super().print_blockchain(head)

    def set_mining_strategy(self, mine_strategy):
        self.mine_strategy = mine_strategy
        self.mine_strategy.setup(self)


