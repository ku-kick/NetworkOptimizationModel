"""
Optimizes simulation through adjusting max throughput fractions available to
the virtualized environments.
"""

from dataclasses import dataclass
import linsmat
import ut
import random
import copy

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
		list.__init__(self, *args, **kwargs)
		self.quality = None

	@staticmethod
	def make_row_index_from_helper_virt(helper_virt):
		"""
		Creates RowIndex translating indices into a position in the current
		vector
		"""
		schema = helper_virt.env.schema
		variables = GaGeneVirt._helper_virt_as_index_var_list(helper_virt)
		row_index = linsmat.RowIndex.make_from_schema(schema, variables)

		return row_index

	@staticmethod
	def new_from_helper_virt(helper_virt: linsmat.HelperVirt):
		"""
		Creates new gene using linsmat.HelperVirt
		"""
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
		"""
		Converts the instance into DataInterface. It ensures interoperability
		of the representation w/ the rest of the project
		"""
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
					pos = row_index.get_pos(var, rho=rho, **indices)
					s += self[pos]

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
	- Generate population of size n_species
	* Cross n_cross random species
	- Run simulation
	- Exclude ceil(fraction_worst * population_size) performers
	- Generate ceil(fraction_worst * population_size) random species
	- if out of iteration, end, else, go to *
	"""

	SWAP_PERC_GENES = .5  # Fraction of genes to be swapped. See `indiv_cross_random_swap`
	SWAP_PERC_POPULATION = .3  # Fraction of individuals from the entire population that will be selected for crossing
	POPULATION_SIZE = 20
	N_ITERATIONS = 30
	REMOVE_PERC_POPULATION = .3

	simulation_constructor: object  # Callable `fn(data_interface, schema) -> Simulation`
	helper_virt: linsmat.HelperVirt
	conf_swap_frac_genes: float = SWAP_PERC_GENES

	def __post_init__(self):
		self._population = list()

	def indiv_cross_random_swap(self, ind_a, ind_b):
		"""
		Crosses individuals through random swapping
		"""
		assert(len(ind_a) == len(ind_b))
		n_ids = int(len(ind_a) * self.conf_swap_frac_genes)
		ids = random.sample(range(len(ind_a)), n_ids)

		for i in ids:
			swap = ind_a[i]
			ind_a[i] = ind_b[i]
			ind_b[i] = swap

		ind_a.normalize(self.helper_virt)
		ind_b.normalize(self.helper_virt)

		return ind_a, ind_b

	def population_range(self, population=None, copy_=False):
		"""
		:param population: if None, `self.population` is used
		:param copy: if True, deep copy will be performed
		"""
		if population is None:
			population = self._population

		if copy_:
			population = copy.deepcopy(population)

		population = sorted(population, key=lambda item: item.quality)

		return population

	def population(self):
		return self._population

	def _population_generate_append(self, n):
		population_new = self._population_generate(n)
		self._population.extend(population_new)

	def _population_generate(self, n):
		"""
		Generates species, normalizes their weights, and appends those to the
		gene pool.
		"""
		population_new = list(map(lambda i: GaGeneVirt.new_from_helper_virt(self.helper_virt), range(n)))

		for indiv in population_new:
			for i in range(len(indiv)):
				indiv[i] = random.uniform(0, 1)

			indiv.normalize(self.helper_virt)  # Rho-s, i.e. fractions of intensity, must sum up to 1

		return population_new

	def _population_cross_fraction_random(self, fraction=SWAP_PERC_POPULATION):
		"""
		Selects int(POPULATION_SIZE * fraction) species from the population to
		perform
		"""
		# Infer the number of crossed species, and
		n = int(len(self.population()) * fraction)
		n = n - (n % 2)

		# Get a random sample (rand. uniform)
		sample = random.sample(self._population, n)
		group_size = len(sample) // 2

		# Split the group
		group_a = sample[:group_size]
		group_b = sample[group_size:]

		# Perform cross, normalize afterwards
		for a, b in zip(group_a, group_b):
			a, b = self.indiv_cross_random_swap(a, b)
			a.normalize(self.helper_virt)
			b.normalize(self.helper_virt)

	def _population_update_sim(self):
		"""
		Constructs and runs simulations consecutively, using species from the
		population as simulation parameters.
		"""
		for indiv in self.population():
			data_interface = indiv.as_data_interface(self.helper_virt)
			schema = self.helper_virt.env.schema
			sim = self.simulation_constructor(data_interface, schema)
			sim.run()
			indiv.quality = sim.quality()

	def _population_remove_n_first(self, n):
		assert n < len(self._population) - 1
		self._population = self._population[n:]

	def _population_fraction_to_int(self, fraction):
		return int(len(self._population) * fraction)

	def run(self, n_iterations=N_ITERATIONS):
		"""
		Runs `n_iterations` iterations, ranges the candidates, and returns the best one
		"""
		self._population_generate_append(self.POPULATION_SIZE)
		assert n_iterations > 1

		for _ in range(n_iterations):
			self._population_cross_fraction_random()
			self._population_update_sim()
			self.population_range()
			n_worst = self._population_fraction_to_int(self.REMOVE_PERC_POPULATION)
			self._population_remove_n_first(n_worst)  # The population has already been sorted according to the quality measure
			self._population_generate_append(n_worst)  # Replace the removed members of the population

		self._population_update_sim()
		self.population_range()

		return self._population[-1]
