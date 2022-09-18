import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import sim, cli, linsolv_planner
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

	def setUp(self) -> None:
		psi_upper = 10
		phi_upper = 10
		v_upper = 10
		x_eq_upper = 10
		tl_upper = 500
		mm_psi_upper = psi_upper / tl_upper
		mm_phi_upper = phi_upper / tl_upper
		mm_v_upper = v_upper / tl_upper

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
				output=self.__CSV_OUTPUT_FILE
			)

	def test_pygal(self):
		"""
		Just a test plot to get started rapidly w/ plotting routines when debugging / tracking the simulation
		"""
		chart = pygal.XY(stroke=False, style=pygal.style.RedBlueStyle)
		chart.title = ''
		signal_len = 100
		signal = list(zip(list(range(1, signal_len)), list(map(lambda i: i * math.log2(i), range(1, signal_len)))))
		signal2 = list(zip(list(range(1, signal_len)), list(map(lambda i: -i * math.log2(i), range(1, signal_len)))))
		chart.add('set1', signal)
		chart.add('set2', signal2)
		chart.render_to_png("out.svg")

	def test_run_sim(self):
		simulation = sim.Simulation.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE,
			row_index_variables=[])
		ls_planner = linsolv_planner.LinsolvPlanner(simulation.data_interface, simulation.schema)
		ls_planner.solve()  # Populate the output CSV
		# simulation.data_interface.sync()
		simulation.reset()
		simulation.run()
		graph_renderer = cli.Format.simulation_trace_graph_scatter(simulation=simulation,
			variables=["x^", "y^", "z^", "g^"])
		graph_renderer.output()


if __name__ == "__main__":
	unittest.main()
