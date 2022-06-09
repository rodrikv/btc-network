import hashlib
from sim import util

class BaseTable:
    def __init__(self, buckets, slots):
        self._buckets = buckets
        self._slots = slots
        self._elems = [Bucket(slots=slots)
                       for _ in range(buckets)]
        self.data = dict()

    def __len__(self):
        return sum(map(len, self.elems))

    def __getitem__(self, item):
        return self._elems[item]

    def __delitem__(self, key):
        self._elems[key].clear()

    def __eq__(self, other):
        return self.slots == other.slots and \
            self.buckets == other.buckets and \
            self.elems == other.elems

    def clear(self):
        for bucket in self._elems:
            bucket.clear()

    @property
    def elems(self):
        return tuple(self._elems)

    @property
    def buckets(self):
        return self._buckets

    @property
    def slots(self):
        return self._slots

    def add(self, ip, timstamp):
        pass

    def update(self, ip: util.SimpleAddress, timestamp):
        if ip not in self.data:
            return

        pe = self.data[ip]['object']
        pe.set_timestamp(timestamp)

    def delete(self, ip: util.SimpleAddress):
        if ip not in self.data:
            return

        bucket = self.data[ip]['bucket']
        slot = self.data[ip]['slot']
        del self.data[ip]
        self.elems[bucket][slot] = None


class NewTable(BaseTable):
    def __init__(self, buckets = 256, slots = 64):
        super().__init__(buckets = buckets, slots = slots)

    def newbucket(self, my_addr: util.SimpleAddress, new_addr: util.SimpleAddress, buckets=256):
        i = util.hash(new_addr.group, my_addr.group) % 32
        return util.hash(new_addr.group, i) % buckets

    def newslot(self, my_addr: util.SimpleAddress, new_addr: util.SimpleAddress, buckets=256, slots=64):
        pos = self.newbucket(my_addr, new_addr, buckets=buckets * slots)
        return pos // slots, pos % slots


    def add(self, src_addr: util.SimpleAddress, addr: util.SimpleAddress, timestamp):
        pe = PeerEntry(addr, timestamp)
        i, j = self.newslot(src_addr, addr)
        self.elems[i][j] = pe
        self.data[addr] = pe
        self.data[addr] = {
            'bucket': i,
            'slot': j,
            'object': pe
        }


class TriedTable(BaseTable):
    def __init__(self, buckets = 64, slots = 64):
        super().__init__(buckets = buckets, slots = slots)

    def triedbucket(self, addr: util.SimpleAddress, buckets=64):
        i = util.hash(addr) % 4
        return util.hash(addr.group, i) % buckets

    def triedslot(self, addr: util.SimpleAddress, buckets=64, slots=64):
        pos = self.triedbucket(addr, buckets=buckets * slots)
        return pos // slots, pos % slots

    def add(self, addr: util.SimpleAddress, timestamp):
        pe = PeerEntry(addr, timestamp)
        i, j = self.triedslot(addr)
        self.elems[i][j] = pe
        self.data[addr] = {
            'bucket': i,
            'slot': j,
            'object': pe
        }

class PeerEntry:
    def __init__(self, ip, timestamp=None):
        self._ip = ip
        self._timestamp = timestamp

    @property
    def ip(self):
        return self._ip

    def set_timestamp(self, timestamp):
        self._timestamp = timestamp

    @property
    def timestamp(self):
        return self._timestamp

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    def __le__(self, other):
        return self.timestamp <= other.timestamp

    def __eq__(self, other):
        if not other:
            return False
        return self.ip == other.ip and \
               self.timestamp == other.timestamp

class Bucket:
    def __init__(self, slots = 64):
        self._slots = slots
        self._elems = [None for _ in range(self.slots)]
        self._len = 0

    def __len__(self):
        return self._len

    def __getitem__(self, item):
        return self._elems[item]

    def __setitem__(self, key, value):
        if not self._elems[key] and value:
            if self._len == self.slots:
                deleted_index = self._is_terrible()
                key = deleted_index
            self._len += 1
        elif self._elems[key] and not value:
            self._len -= 1
        self._elems[key] = value

    def __delitem__(self, key):
        if self._elems[key]:
            self._len -= 1
        self._elems[key] = None

    def __eq__(self, other):
        return self.slots == other.slots and \
            self.elems == other.elems

    def clear(self):
        for i in range(self.slots):
            self._elems[i] = None
        self._len = 0

    @property
    def elems(self):
        return tuple(self._elems)

    @property
    def slots(self):
        return self._slots