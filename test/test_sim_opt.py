import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import cli, linsmat, ut, linsolv_planner
import functools
import os
import math
from generic import Log
import logging
import ut
import sim_opt
import simulation


log = ut.Log(file=__file__, level=ut.Log.LEVEL_VERBOSE)


class TestSimOpt(unittest.TestCase):
	__HERE = pathlib.Path(os.path.realpath(__file__)).parent
	__SCHEMA_FILE = str((__HERE / "test_schema_3.json").resolve())
	__CSV_OUTPUT_FILE = str((__HERE / "test_sim_output.csv").resolve())

	def setUp(self) -> None:
		psi_upper = 40
		phi_upper = 30
		v_upper = 70
		x_eq_upper = 200
		tl_upper = 500
		mm_psi_upper = psi_upper / tl_upper
		mm_phi_upper = phi_upper / tl_upper
		mm_v_upper = v_upper / tl_upper
		self.schema = linsmat.Schema(filename=self.__SCHEMA_FILE)
		entry_nodes = list(map(lambda rho: dict(j=0, l=0, rho=rho), range(self.schema.get_index_bound("rho"))))

		if not os.path.exists(self.__CSV_OUTPUT_FILE):
			cli.generate_random(
				schema=self.__SCHEMA_FILE,
				psi_upper=psi_upper,
				phi_upper=phi_upper,
				v_upper=v_upper,
				x_eq_upper=x_eq_upper,
				mm_psi_upper=mm_psi_upper,
				mm_phi_upper=mm_phi_upper,
				mm_v_upper=mm_v_upper,
				tl_upper=tl_upper,
				entry_nodes=entry_nodes,
				output=self.__CSV_OUTPUT_FILE
			)
		self.env = linsmat.Env.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE,
			row_index_variables=[], zeroing_data_interface=True)
		self.helper_virt = linsmat.HelperVirt(env=self.env)

	def test_population_generation(self):
		"""
		Run population generator, check whether normalization is successful
		"""
		ga_sim_virt_opt = sim_opt.GaSimVirtOpt(simulation_constructor=None, helper_virt=self.helper_virt)
		n = 2
		ga_sim_virt_opt._population_generate_append(n=n)
		s = 0.0

		for gene in ga_sim_virt_opt.population():
			s += sum(gene)

		log.debug("s", s)
		self.assertTrue(s > 0.0)
		self.assertTrue(math.isclose(s % 1.0, 0, abs_tol=0.0001))

	def test_population_run(self):
		"""
		Initializes a population and runs a sequence of simulations each of
		which is associated with an individual from the population.
		"""
		ga_sim_virt_opt = sim_opt.GaSimVirtOpt(simulation_constructor=simulation.Simulation.from_dis, helper_virt=self.helper_virt)
		n = 10
		ga_sim_virt_opt._population_generate_append(n=n)
		ga_sim_virt_opt._population_update_sim()

		for indiv in ga_sim_virt_opt.population():
			log.debug("GA, species", str(indiv))
		log.debug("GA output, quality functions", list(map(lambda i: i.quality, ga_sim_virt_opt.population())))


if __name__ == "__main__":
	unittest.main()
