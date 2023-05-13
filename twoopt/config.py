"""

WARNING! This module is obsolete. Do not use it.

For various cases, different sets of configs may be required. This module
provides useful shortcuts for overriding configurations globally, for the entire
project.

Naming practices by example:
- OPT_VIRT_GA_SWAP_PERC_GENES = .5
	- OPT - optimization
	- VIRT - virtualized network (there may be other variants)
	- GA - genetic algorithm
	- SWAP_PERC_GENES - domain specific configs
- OPT_VIRT_ORCHESTRATION_N_ITERATIONS = 2
	- ORCHESTRATION - the API glue that ensures data flow between the optimizers
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
	OPT_VIRT_ORCHESTRATION_N_ITERATIONS = 20  # Number of network optimizing iterations
	_CONFIGS = [k for k, v in locals().items() if not k.startswith('_')]  # A complete list of configs


class _TestGenericCfg(_DefaultCfg):
	"""
	Optimized for performance.
	"""
	OPT_VIRT_GA_POPULATION_SIZE = 3
	OPT_VIRT_GA_SWAP_PERC_POPULATION = 1.0  # Fraction of individuals from the entire population that will be selected for crossing
	OPT_VIRT_GA_REMOVE_PERC_POPULATION = .6  # % of population to be removed
	OPT_VIRT_GA_N_ITERATIONS = 2
	OPT_VIRT_GA_N_ITERATIONS = 2
	OPT_VIRT_ORCHESTRATION_N_ITERATIONS = 2


cfg = _DefaultCfg()


def cfg_set(inst):
	global cfg

	for key in _DefaultCfg._CONFIGS:
		setattr(cfg, key, getattr(inst, key))


def cfg_set_default():
	"""
	Apply default cfgs
	"""
	cfg_set(_DefaultCfg)


def cfg_set_test():
	"""
	Set testing cfg.
	"""
	cfg_set(_TestGenericCfg)
