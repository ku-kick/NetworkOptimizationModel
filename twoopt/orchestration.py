"""
API glue.

Linear solver and simulation optimizer have to be "in agreement". I.e they have
to operate upon the same ontology and data.

This module contains entities that fullfill 2 purposes.
1. They glue relevant pairs of linear programming and simulation optimizers together,
2. Complete up the optimization algorithm, ensuring data flow between the
optimizers, and checking for stop conditions.
"""

import sim_opt
import linsmat
import linsolv_planner
from dataclasses import dataclass
import simulation

@dataclass
class VirtOpt:
	"""
	The '22 paper.
	- Minimize loss (z)
	- Maximize processing (g)
	"""
	CONF_STOP_N_ITERATIONS = 20
	CONF_GA_GENE_SWAP_PERCENTAGE = .3
	CONF_GA_POPULATION_SIZE = 30
	CONF_GA_N_ITERATIONS = 10
	CONF_GA_WORST_PERCENTAGE = .2  # Worst performers will be removed and replaced on each iteration
	CONF_GA_SWAP_POPULATION_PERCENTAGE = .4  # Random individuals will be subjected to crossing

	schema_path: str  # Path to .json schema file
	storage_path: str  # Path to .csv storage file
	conf_stop_n_iterations = CONF_STOP_N_ITERATIONS

	def __post_init__(self):
		# Construct ETL entities
		self.schema = linsmat.Schema(filename=self.schema_path)
		self.csv_provider = linsmat.PermissiveCsvBufferedDataProvider(csv_file_name=self.storage_path)
		self.csv_data_interface = linsmat.DataInterface(provider=self.csv_provider, schema=self.schema)
		self.ram_provider = linsmat.DictRamDataProvider()
		self.ram_data_interface = linsmat.DataInterface(provider=self.ram_provider, schema=self.schema)
		self.ram_data_interface.update(self.csv_data_interface)  # Ensure consistency
