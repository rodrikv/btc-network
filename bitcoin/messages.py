"""
This module contains the various message types that can be sent over the Bitcoin network.
"""

import sys

sys.path.append("..")

from sim.base_models import *


class InvMessage(Item):
    """Represents INV messages used to announce new blocks."""
    def __init__(self, item_id: str, type: str, sender_id: str):
        """
        Create an InvMessage object.
        * item_id (str): Id of the block/transaction being announced.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        super().__init__(sender_id, 100)
        self.size = 100
        self.item_id = item_id
        self.type = type


class GetDataMessage(Item):
    """Represents GET_DATA messages used to request blocks after receiving INV messages."""
    def __init__(self, item_id: str, type: str, sender_id: str):
        """
        Create a GetDataMessage object.
        * item_id (str): Id of the block/transaction being requested.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        super().__init__(sender_id, 100)
        self.size = 100
        self.item_id = item_id
        self.type = type

class PingMessage(Item):
    """Represents PING messages used to primarily confirm that the TCP/IP connection is still valid."""
    def __init__(self, sender_id: str):
        """
        Create a PingMessage object.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        super().__init__(sender_id, 8)
        self.size = 8
        self.type = type

class PongMessage(Item):
    """"Represents PONG messages used to send in response to PING messages."""
    def __init__(self, sender_id: str):
        """
        Create a PongMessage object.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        super().__init__(sender_id, 8)
        self.size = 8
        self.type = type


class VerAckMessage(Item):
    """Represents VerAck messages"""
    def __init__(self, sender_id: str, sender_node):
        """
        Create a VerAckMessage object.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        super().__init__(sender_id, 20, sender_node=sender_node)
        self.size = 20
        self.type = type

class AddressMessage(Item):
    """Represents ADDRESS messages"""
    def __init__(self, sender_id: str, nodes: List[Node]):
        """
        Create a AddressMessage object.
        * sender_id (str): Id of the sender node. Can be used as a return address.
        * size (float): size of the item in bytes.
        """
        super().__init__(sender_id, 30)
        self.size = 30
        self.type = type
        self.value = nodes