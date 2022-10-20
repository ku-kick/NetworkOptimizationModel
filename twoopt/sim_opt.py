"""
Optimizes simulation through adjusting max throughput fractions available to
the virtualized environments.
"""

from dataclasses import dataclass
import linsmat
import ut
import random

log = ut.Log(file=__file__, level=ut.Log.LEVEL_DEBUG)

class GaGeneVirt(list):

	@staticmethod
	def _helper_virt_as_index_var_list(helper_virt: linsmat.HelperVirt):
		return [
			helper_virt.var_transfer_intensity_fraction,
			helper_virt.var_store_intensity_fraction,
			helper_virt.var_process_intensity_fraction,
		]

	def __init__(self, *args, **kwargs):
		self.row_index = kwargs.pop("row_index", None)
		list.__init__(self, *args, **kwargs)

	@staticmethod
	def make_row_index_from_helper_virt(helper_virt):
		schema = helper_virt.env.schema
		variables = GaGeneVirt._helper_virt_as_index_var_list(helper_virt)
		row_index = linsmat.RowIndex.make_from_schema(schema, variables)

		return row_index

	@staticmethod
	def new_from_helper_virt(helper_virt: linsmat.HelperVirt):
		schema = helper_virt.env.schema
		variables = GaGeneVirt._helper_virt_as_index_var_list(helper_virt)
		row_index = linsmat.RowIndex.make_from_schema(schema, variables)
		data_interface = helper_virt.env.data_interface
		ret = GaGeneVirt([0 for _ in range(row_index.get_row_len())])

		for var in variables:
			for indices in schema.radix_map_iter_var_dict(var):
				pos = row_index.get_pos(var, **indices[1])
				log.debug(GaGeneVirt, "var", var, "indices", indices[1], "pos", pos)
				val = data_interface.get(var, **indices[1])
				ret[pos] = val

		return ret

	def as_data_interface(self, helper_virt):
		schema = helper_virt.env.schema
		variables = self._helper_virt_as_index_var_list(helper_virt)
		row_index = self.make_row_index_from_helper_virt(helper_virt)
		data_interface = helper_virt.env.data_interface.clone_as_dict_ram()

		for var in variables:
			for indices in schema.radix_map_iter_var_dict(var):
				pos = row_index.get_pos(var, **indices[1])
				val = self[pos]
				data_interface.set(var, val, **indices[1])

		return data_interface

	def normalize(self, helper_virt):
		"""
		Normalizes fractions of intensity, so they sum up to 1.0
		"""
		row_index = self.make_row_index_from_helper_virt(helper_virt)

		for var in self._helper_virt_as_index_var_list(helper_virt):
			assert "rho" in helper_virt.env.schema.get_var_indices(var)  # The fraction is associated w/ `rho` index, and it should not be changed
			var_indices = helper_virt.env.schema.get_var_indices(var)  # Get list of indices
			var_indices = list(filter(lambda i: i != "rho", var_indices))  # "rho" is the index to be normalized against
			rho_bound = helper_virt.env.schema.get_index_bound("rho")

			for indices in helper_virt.env.schema.radix_map_iter_dict(*var_indices):
				s = 0.0

				# Accumulate sum
				for rho in range(rho_bound):
					s += row_index.get_pos(var, rho=rho, **indices)

				frac = 1 / s

				# Normalize members
				for rho in range(rho_bound):
					pos = row_index.get_pos(var, rho=rho, **indices)
					self[pos] *= frac


@dataclass
class GaSimVirtOpt:
	"""
	Reshuffles throughput fractions according to a simple GeneticAlgorithm.
	Stops as soon as the iterations thresold has been exceeded.

	GA:
	1. Generate population of size n_species
	2. Run simulation
	3. Pick n_best best candidates (n >> n_species / 2)
	4. Generate n_species - n - n_offsprings random species (the "random
	   group")
	5. Cross (1) n_offsprings / 2 species from n_best and
	   some (2) n_offsprings / 2 species from the random group
	6. Cross (1) 1 - n_offsprings / 2 species from n_best w/ e/o
	7. If n_iterations has been exceeded, stop. Go to 1. otherwise
	"""

	N_SPECIES_DEFAULT = 50
	N_BEST_DEFAULT = 10
	N_OFFSPRINGS_DEFAULT = 5
	N_ITERATIONS_DEFAULT = 10

	simulation_constructor: object  # Callable `fn(data_interface, schema) -> Simulation`
	helper_virt: linsmat.HelperVirt
	conf_n_species: int = N_SPECIES_DEFAULT
	conf_n_best: int = N_BEST_DEFAULT
	conf_n_offsprings: int = N_OFFSPRINGS_DEFAULT
	conf_n_iterations: int = N_ITERATIONS_DEFAULT

	def __post_init__(self):
		self._population = list()

	def population(self):
		return self._population

	def _population_generate_append(self, n):
		population_new = list(map(lambda i: GaGeneVirt.new_from_helper_virt(self.helper_virt), range(n)))

		for indiv in population_new:
			for i in range(len(indiv)):
				indiv[i] = random.uniform(0, 1)

			indiv.normalize(self.helper_virt)  # Rho-s, i.e. fractions of intensity, must sum up to 1

