import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import sim, cli, linsolv_planner, linsmat
from sim import sim
import os
import pathlib
import math
import pygal


class TestSim(unittest.TestCase):
	__HERE = pathlib.Path(os.path.realpath(__file__)).parent
	__SCHEMA_FILE = str((__HERE / "test_schema_3.json").resolve())
	__CSV_OUTPUT_FILE = str((__HERE / "test_sim_output.csv").resolve())
	#TODO implement test run and produce a trace output (see Simulation.Trace)

	def __init__(self, *args, **kwargs):
		unittest.TestCase.__init__(self, *args, **kwargs)

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
			self.sim_run()
			self.sim_visualize()
		self.env = linsmat.Env.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE,
			row_index_variables=[])

	def sim_run(self):
		self.simulation = sim.Simulation.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE,
			row_index_variables=[])
		ls_planner = linsolv_planner.LinsolvPlanner(self.simulation.data_interface, self.simulation.schema)
		ls_planner.solve()  # Populate the output CSV
		# simulation.data_interface.sync()
		self.simulation.reset()
		self.simulation.run()

	def sim_visualize(self):
		graph_renderer = cli.Format.simulation_trace_graph_scatter(simulation=self.simulation,
			variables = ["x^", "y^", "z^", "g^"])
		graph_renderer.output()

	def test_run_sim_balance(self):
		data_interface = self.env.data_interface

if __name__ == "__main__":
	unittest.main()
