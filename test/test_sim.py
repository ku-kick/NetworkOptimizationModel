import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import *
import os
import pathlib
import math
import pygal


class TestData(unittest.TestCase):
	__HERE = pathlib.Path(os.path.realpath(__file__)).parent
	__SCHEMA_FILE = str((__HERE / "test_schema_3.json").resolve())
	__CSV_OUTPUT_FILE = str((__HERE / "test_sim_output.csv").resolve())
	#TODO implement test run and produce a trace output (see Simulation.Trace)

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
		simulation = sim.sim.Simulation.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE)
		simulation.run()
		graph_renderer = cli.Format.simulation_trace_graph_scatter(simulation=simulation,
			variables=["x^", "y^", "z^", "g^"])
		graph_renderer.output()


unittest.main()
