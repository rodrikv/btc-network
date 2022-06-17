import random
from sim.base_models import NodeStorage
from bitcoin.models import Miner
from sim.util import Region
from bitcoin.tx_modelings import NoneTxModel
from bitcoin.mining_strategies import SelfishMining, HonestMining, NullMining

from zelig import Simulation

""" CONFIGURING WITH CODE """

# create the  simulator object and set up the main parameters
sim = Simulation()
sim.set_log_level('INFO')
sim.name = 'selfish_mine_test'
sim.results_dir = '/home/tuna/Desktop/temp'
sim.sim_reps = 1
sim.sim_iters = 10000
sim.iter_seconds = 0.1
sim.block_int_iters = 6000
sim.max_block_size = 1000000
sim.tx_modeling = NoneTxModel()
sim.dynamic = False
sim.block_reward = 100

# potential network topologies
ring = lambda n1, n2: abs(n1.id - n2.id) == 1 or abs(n1.id - n2.id) == 9
star = lambda n1, n2: n1.name == 'center' or n2.name == 'center'
rand = lambda n1, n2: n2.id in [random.randint(0, 32) for _ in range(3)]
mesh = lambda n1, n2: True
sim.connection_predicate = mesh

# mining strategies as singletons
selfish_mining = SelfishMining()
honest_mining = HonestMining()
null_mining = NullMining()

selfish_power, honest_power = 40, 60

# create miners of two different types
# selfish_miner = Miner('SELFISH', selfish_power, Region('US'), sim.iter_seconds)
# selfish_miner.mine_strategy = selfish_mining
# selfish_miner.node_storage = sim.node_storage
# sim.add_node(selfish_miner)
for i in range(40):
    honest_miner = Miner(f'HONEST_{i}', honest_power, Region('US'), sim.iter_seconds)
    honest_miner.mine_strategy = honest_mining
    honest_miner.node_storage = sim.node_storage
    sim.add_node(honest_miner)

# populate network with full nodes
for i in range(30):
    full_node = Miner(f'FULL_{i}', 10, Region('US'), sim.iter_seconds)
    full_node.mine_strategy = null_mining
    full_node.node_storage = sim.node_storage
    sim.add_node(full_node)

for node in sim.nodes:
    sim.node_storage.add(node)
sim.run(report_time=True, track_perf=False)

for message_format, messages in sim.message_storage.messages.items():
    print(f'{message_format}: {len(messages)}')