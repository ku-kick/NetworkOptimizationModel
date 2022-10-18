"""
Optimizes simulation through adjusting max throughput fractions available to
the virtualized environments.
"""

from dataclasses import dataclass
import linsmat


class GaGeneVirt(list):

	@staticmethod
	def _helper_virt_as_index_var_list(helper_virt: linsmat.HelperVirt):
		return [
			helper_virt.var_transfer_intensity_fraction,
			helper_virt.var_store_intensity_fraction,
			helper_virt.var_process_intensity_fraction,
		]

	@staticmethod
	def new_from_helper_virt(helper_virt: linsmat.HelperVirt):
		schema = helper_virt.schema
		variables = self._helper_virt_to_index_var_list(helper_virt)
		row_index = linsmat.RowIndex.make_from_schema(schema, variables)
		data_interface = helper_virt.env.data_interface
		ret = GaGeneVirt([0 for _ in range(row_index.get_row_len())])

		for var in variables:
			for indices in schema.radix_map_iter_var_dict(var):
				pos = row_index.get_pos(var, **indices)
				val = data_interface.get(var, **indices)
				ret[pos] = val

		return ret


	def as_data_interface(self, helper_virt):
		schema = helper_virt.schema
		variables = self._helper_virt_to_index_var_list(helper_virt)
		row_index = linsmat.RowIndex.make_from_schema(schema, variables)
		data_interface = helper_virt.env.data_interface.clone_as_dict_ram()
		ret = linsmat.Data

		for var in variables:
			for indices in schema.radix_map_iter_var_dict(var):
				pos = row_index.get_pos(var, **indices)
				val = self[pos]
				data_interface.set(var, **indices)


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

	simulation_constructor: object  # Callable `fn(data_interface) -> Simulation`
	data_interface: object
	conf_n_species: int = N_SPECIES_DEFAULT
	conf_n_best: int = N_BEST_DEFAULT
	conf_n_offsprings: int = N_OFFSPRINGS_DEFAULT
	conf_n_iterations: int = N_ITERATIONS_DEFAULT


