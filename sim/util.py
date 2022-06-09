"""
Various utility classes and methods.
"""

import uuid
from enum import Enum
import numpy as np
import math
import hashlib


MAX_INCOMING_CONNECTIONS = 117
MAX_OUTGOING_CONNECTIONS = 8


class Region(Enum):
    """The supported regions."""
    US = 'US'
    RU = 'RU'
    KZ = 'KZ'
    ML = 'ML'
    CN = 'CN'
    GE = 'GE'
    NR = 'NR'
    VN = 'VN'
    CH = 'CH'

def triedprob(rho, omega):
    """Probability an IP is seeded from the tried table.

    :param rho: (float) proportional size of tried table to new table.
    :param omega: (float) number of connected outgoing peers
    """
    rho_freq = math.sqrt(rho) * (9 - omega)
    return rho_freq / (1 + omega + rho_freq)

def hash(*inputs):
    preimage = ''.join(map(str, inputs))
    return int(hashlib.md5(preimage.encode('utf-8')).hexdigest(), 16)

def singleton(class_):
    instances = {}

    def get_instance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return get_instance


def generate_uuid() -> str:
    """
    Generate UUIDs to use as `sim.base_models.Item` ids.
    """
    return str(uuid.uuid4())


class SimpleAddress:
    """
    Generate IP Address to use for `sim.base_models.Node` id.
    """

    def __init__(self, group, ip):
        self._group = str(group)
        self._ip = str(ip)
        self._str = '%s:%s' % (self.group, self.ip)

    @property
    def group(self):
        return self._group

    @property
    def ip(self):
        return self._ip

    def __str__(self):
        return self._str

    def __eq__(self, other):
        return self.ip == other.ip and \
               self.group == other.group

    def __hash__(self):
        return hash(repr(self))

    @staticmethod
    def randomaddress(rand=np.random, groups=None):
        group = rand.choice(groups) if groups else \
            rand.randint(1, 65536)
        ip = rand.randint(0, 65536)
        return SimpleAddress(group, ip)