"""
For various cases, different sets of configs may be required. This module
provides useful shortcuts for overriding configurations globally, for the entire
project.

Naming conventions by example:
- OPT_VIRT_GA_SWAP_PERC_GENES = .5
	- OPT - optimization
	- VIRT - virtualized network (there may be other variants)
	- GA - genetic algorithm
	- SWAP_PERC_GENES - domain specific configs
"""


class _DefaultCfg:
	"""
	"Production-grade".
	"""
	OPT_VIRT_GA_SWAP_PERC_GENES = .5  # Fraction of genes to be swapped. See `indiv_cross_random_swap`
	OPT_VIRT_GA_SWAP_PERC_POPULATION = .3  # Fraction of individuals from the entire population that will be selected for crossing
	OPT_VIRT_GA_POPULATION_SIZE = 20
	OPT_VIRT_GA_N_ITERATIONS = 30
	OPT_VIRT_GA_REMOVE_PERC_POPULATION = .3  # % of population to be removed


class _TestGenericCfg(_DefaultCfg):
	"""
	Optimized for performance.
	"""
	OPT_VIRT_GA_POPULATION_SIZE = 6
	OPT_VIRT_GA_N_ITERATIONS = 2
	OPT_VIRT_GA_N_ITERATIONS = 2


cfg = _DefaultCfg()


def cfg_switch_default():
	"""
	Apply default cfgs
	"""
	global cfg

	cfg = _DefaultCfg()


def cfg_switch_test():
	"""
	Set testing cfg.
	"""
	global cfg

	cfg = _TestGenericCfg()
