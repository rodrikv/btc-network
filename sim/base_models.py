"""
The classes that make up the core simulator.
"""
from decimal import DivisionByZero
import logging
import math

from loguru import logger

from typing import List, Dict

from sim import util
from sim.network_util import get_delay, Region

from bitcoin.tables import *
import random
import os
import time
# from bitcoin.messages import VersionMessage


class Item:
    """Represents objects that can be transmitted over a network (e.g. blocks, messages)."""

    def __init__(self, sender_id: str, size: float, sender_node = None):
        """
        Create an Item object.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        self.id = util.generate_uuid()
        self.size = size
        self.sender_id = sender_id
        self.sender_node = sender_node


class VersionMessage(Item):
    """Represents VERSION messages"""
    def __init__(self, sender_id: str, sender_node):
        """
        Create a GetDataMessage object.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        super().__init__(sender_id, 185, sender_node=sender_node)
        self.size = 185
        self.type = type


class Block(Item):
    """Represents a block to be stored on the blockchain."""

    def __init__(self, creator, prev_id: str, height: int):
        """
        Create a Block object.

        * miner (`Node`): Node that created the block.
        * prev_id (str): Id of the block this block was mined on top of.
        * height (int): Height of the block in the blockchain.
        """
        super().__init__(None, 0)
        self.prev_id = prev_id
        self.miner = creator.name
        self.created_at = creator.timestamp
        self.height = height
        self.size = 0
        self.tx_count = 0
        self.transactions = []
        self.reward: Reward = None

    def add_tx(self, tx):
        self.transactions.append(tx)
        self.size += tx.size
        self.tx_count += 1

    def has_tx(self, tx):
        return tx in self.transactions

    def __getstate__(self):
        state = self.__dict__.copy()
        del state['sender_id']
        del state['size']
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def __str__(self) -> str:
        return f'BLOCK (id:{self.id}, prev: {self.prev_id})'


class GetAddrMessage(Item):
    """Represents GetAddr messages"""
    def __init__(self, sender_id: str):
        super().__init__(sender_id, 20)
        self.type = type
        self.size = 20


class Packet:
    """Wrapper class for transmitting `Item` objects over the network."""

    def __init__(self, payload: Item):
        """
        Create a Packet object.
        * payload (`Item`): Item contained in the packet.
        """
        self.payload = payload
        self.reveal_at = 0


class Node:
    """Represents the participants in the blockchain system."""

    def __init__(self, iter_seconds, name, region, timestamp=0):
        """
        Create a Node object.
        * region (`sim.util.Region`): Geographic region of the node.
        * timestamp (int): Initial timestamp of the node. Defaults to zero.
        """
        self.id = util.SimpleAddress.randomaddress()
        self.name = name
        self.timestamp = timestamp
        self.region = region
        self.iter_seconds = iter_seconds

        self.blockchain: Dict[str, Block] = dict()
        """A dictionary that stores `BTCBlock` ids as keys and `BTCBlock`s as values."""

        self.inbox: Dict[int, List[Packet]] = dict()
        """Node's inbox with simulation timestamps as keys and lists of `Item`s to be consumed at that timestamp as values."""

        self.ins: Dict[str, Node] = dict()
        """Dictionary storing incoming connections. Keys are `Node` ids and values are `Node`s."""

        self.outs: Dict[str, Node] = dict()
        """Dictionary storing outgoing connections. Keys are `Node` ids and values are `Node`s."""

        self.last_reveal_times: Dict[str, int] = dict()
        """
        Dictionary with node ids as keys and integers as values. Values correspond to the reveal time of the last message sent to the node with the given id.

        This is used to simulate links that can only  transmit one message at a time. A new message starts transmission only after the previous one has been received.
        """

        self.new_table: NewTable = NewTable()
        """
        A table holding new Nodes that want to connect and havent been seen.
        """

        self.tried_table: TriedTable = TriedTable()
        """
        A table holding tried Nodes that have been seen perviously.
        """

        self.is_online = True

        self.tried_nodes = []

    def __getstate__(self):
        """Return state values to be pickled."""
        state = self.__dict__.copy()
        # Remove the unpicklable entries.
        del state['ins']
        del state['outs']
        del state['inbox']
        del state['timestamp']
        del state['new_table']
        del state['tried_table']
        return state

    def __str__(self) -> str:
        return self.name

    def __setstate__(self, state):
        """Restore state from the unpickled state values."""
        self.__dict__.update(state)

    def step(self, seconds: float) -> List[Item]:
        """
        Perform one simulation step. Increments its timestamp by 1 and returns the list of `Item` objects to act on in that step.
        * seconds (float): How many real-time seconds one simulation step corresponds to.
        """
        if len(self.outs) < util.MAX_OUTGOING_CONNECTIONS and self.timestamp > 400:
            node = self.get_peer(len(self.outs) + 1)
            if node.id not in self.outs and node not in self.tried_nodes:
                self.tried_nodes.append(node)
                self.connect(node)
                self.send_to(node, GetAddrMessage(self.id))
        self.timestamp += 1
        try:
            return [packet.payload for packet in self.inbox.pop(self.timestamp)]
        except KeyError:
            return []

    def fill_new_table(self, sender_id, addresses):
        for address in addresses:
            self.new_table.add(sender_id, address, self.timestamp)

    def fill_tried_table(self, addresses):
        for address in addresses:
            self.tried_table.add(address, self.timestamp)

    def choose_table(self, omega):
        try:
            rho = len(self.tried_table.data) / len(self.new_table.data)
        except ZeroDivisionError:
            rho = 100
        return self.tried_table if util.triedprob(rho, omega) else self.new_table

    def choose_one(self, l):
        return random.choice(l)

    def get_peer(self, omega):
        table = self.choose_table(omega)
        filled_buckets_index = set()
        for data in table.data.values():
            filled_buckets_index.add(data['bucket'])
        index = self.choose_one(list(filled_buckets_index))
        peer_entry = self.choose_one([i for i in table[index] if i])
        node = self.node_storage.get_node(peer_entry.ip)
        return node

    def reset(self):
        """
        Reset node state back to simulation start, deleting connections as well.
        """
        self.timestamp = 0
        self.blockchain = dict()
        self.inbox = dict()
        self.ins = dict()
        self.outs = dict()
        self.last_reveal_times = dict()

    def restart(self):
        current_time = self.timestamp
        self.reset()
        self.timestamp = current_time

    def send_to(self, node, item: Item):
        """
        Send an item to a specific node. Can be used to respond to messages.
        * node (`sim.base_models.Node`): Target node.
        * item (`sim.base_models.Item`): Item to send.
        """
        packet = Packet(item)
        delay = get_delay(self.region, node.region, item.size) / self.iter_seconds
        reveal_time = math.ceil(max(self.timestamp, self.last_reveal_times.get(node.id, 0)) + delay)
        self.last_reveal_times[node.id] = reveal_time
        packet.reveal_at = reveal_time
        try:
            node.inbox[packet.reveal_at].append(packet)
        except KeyError:
            node.inbox[packet.reveal_at] = [packet]

    def preconnect(self, node):
        return node.is_online and len(self.outs) < util.MAX_OUTGOING_CONNECTIONS

    def connect(self, node):
        """
        Establish an outgoing connection to one or more nodes.
        * argv (`sim.base_models.Node`+): Node(s) to establish connections with.
        """
        if self.preconnect(node):
            self.send_to(node, VersionMessage(self.id, self))
            # self.outs[node.id] = node
            # node.ins[self.id] = self
            self.fill_tried_table([node.id])
            node.fill_tried_table([self.id])

    def print_blockchain(self, head: Block = None):
        logger.warning(f'{self.name}')
        logger.warning(f'\tBLOCKCHAIN:')
        for block in self.blockchain.values():
            logger.warning(f'\t\t{block}')


class Reward:
    def __init__(self, node: Node, value: int):
        self.value = value
        self.timestamp = node.timestamp
        self.node = node

@util.singleton
class NodeStorage:
    def __init__(self) -> None:
        self.nodes = {}

    def add(self, node: Node):
        self.nodes[node.id] = node

    def get_node(self, _id):
        return self.nodes[_id] if _id in self.nodes else None

class MessageStorage:
    def __init__(self) -> None:
        self.messages = {}

    def add(self, to, item):
        if item.__class__.__name__ in self.messages:
            if f"[{item.sender_id}] [{to.id}]" in self.messages[item.__class__.__name__]:
                self.messages[item.__class__.__name__][f"[{item.sender_id}] [{to.id}]"] += [item.__dict__]
            else:
                self.messages[item.__class__.__name__][f"[{item.sender_id}] [{to.id}]"] = [item.__dict__]

        else:
            self.messages[item.__class__.__name__] = {
                f"[{item.sender_id}] [{to.id}]" : [item.__dict__]
            }

    def node_result_to_file(self):
        if not os.path.exists('output'):
            os.mkdir('output')

        for message_mode, value in self.messages.items():
            path = os.path.join('output', str(int(time.time())) + '_' + message_mode + '.txt')
            with open(path, 'w') as f:
                for connection, items in value.items():
                    f.write(f'{connection} {len(items)}\n')