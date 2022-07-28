from bitcoin.models import Miner
from sim.util import MAX_INCOMING_CONNECTIONS, SimpleAddress
from typing import List
from bitcoin.messages import AddressMessage, VersionMessage
from bitcoin.mining_strategies import NullMining


class Decoy:
    def __init__(self, iter_seconds, name, region, timestamp=0):
        super().__init__(iter_seconds, name, region, timestamp=timestamp)
        self.is_online = False


class EclipseAttacker(Miner):
    def __init__(self, name, mine_power, region, iter_seconds, timestamp=0):
        mine_power = 50
        super().__init__(name, mine_power, region, iter_seconds, timestamp=timestamp)
        self.name = f'MALICIOUSNODE_{region}'
        self.just_once = False
        self.victim_node = None
        self.next_attempt = self.timestamp + 100
        self.decoy_nodes: List[NullMining] = [
            SimpleAddress.randomaddress() for i in range(1000)]

    def step(self, seconds):
        self.timestamp += 1
        try:
            items = [packet.payload for packet in self.inbox.pop(
                self.timestamp)]
        except KeyError:
            items = []
        for item in items:
            self.consume(item)

        # tx_count = self.tx_per_iter
        # for c in range(tx_count):
        #     self.tx_model.generate(self)

        # if self.consensus_oracle.can_mine(self):
        #     self.mine_strategy.generate_block(self)
        if self.victim_node:
            if self.next_attempt == self.timestamp:
                ins = self.ins.values()
                outs = self.outs.values()
                if self.victim_node not in ins and self.victim_node in outs:
                    self.send_to(self.victim_node, AddressMessage(
                        self.id, self.decoy_nodes))
                elif self.victim_node not in ins and self.victim_node not in outs:
                    self.send_to(self.victim_node,
                                 VersionMessage(self.id, self))

                self.next_attempt = self.timestamp + 5 * 60

    def consume(self, item):
        if type(item) == VersionMessage:
            return
        super().consume(item)

        # snode = self.node_storage.get_node(item.sender_id)
        # if type(item) == PingMessage:
        #     logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED PING MESSAGE FROM {item.sender_id}')
        #     self.send_to(snode, PongMessage(self.id))
        # elif type(item) == PongMessage:
        #     logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED PONG MESSAGE FROM {item.sender_id}')
        # elif type(item) == VerAckMessage:
        #     logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECIEVED VERACK MESSAGE FROM {item.sender_id}')
        #     # if len(self.outs) < util.MAX_OUTGOING_CONNECTIONS
        #     self.outs[item.sender_id] = snode
        # elif type(item) == VersionMessage and self.victim_node == snode:
        #     logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> RECEIVED VERSION MESSAGE FROM {item.sender_id}')
        #     if len(self.ins) < MAX_INCOMING_CONNECTIONS:
        #         # this need to be changed since we cant provide the node itself
        #         self.ins[item.sender_id] = item.sender_node
        #         self.send_to(item.sender_node, VerAckMessage(self.id, self))
        #         logger.debug(f'[{self.timestamp}] {self.name} <{self.id}> SENT VERACK MESSAGE TO {item.sender_id}')
