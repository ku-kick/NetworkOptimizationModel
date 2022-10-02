import unittest
import pathlib
import sys

from scipy.optimize._lsap import linear_sum_assignment

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import sim, cli, linsolv_planner, linsmat, generic
from sim import sim
import os
import pathlib
import math
import pygal
import simulation as sml
import ut

log = ut.Log(file=__file__, level=ut.Log.LEVEL_VERBOSE)


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
		self.env = linsmat.Env.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE,
			row_index_variables=[])
		self.solve()

	def solve(self):
		self.planner = linsolv_planner.LinsolvPlanner(self.env.data_interface, self.env.schema)
		self.planner.solve()
		self.env.data_interface.provider.sync()

	def sim_run(self):
		self.simulation = sim.Simulation.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE,
			row_index_variables=[])
		ls_planner = linsolv_planner.LinsolvPlanner(self.simulation.data_interface, self.simulation.schema)
		ls_planner.solve()  # Populate the output CSV
		# simulation.data_interface.sync()
		self.simulation.reset()
		self.simulation.run()
		self.simulation.data_interface.provider.sync()

	def sim_visualize(self):
		graph_renderer = cli.Format.simulation_trace_graph_scatter(simulation=self.simulation,
			variables = ["x^", "y^", "z^", "g^"])
		# graph_renderer.output()

	def run_sim_balance(self):
		data_interface = self.env.data_interface
		schema = self.env.schema

		def x_processed_or_zero(j, i, rho, l):
			nonlocal data_interface

			if j == i:
				return 0

			return data_interface.get("x^", j=j, i=i, rho=rho, l=l)

		for j, rho, l in self.env.schema.radix_map_iter("j", "rho", "l"):
			x_eq = data_interface.get("x_eq^", j=j, rho=rho, l=l)
			z = data_interface.get("z^", j=j, rho=rho, l=l)
			g = data_interface.get("g^", j=j, rho=rho, l=l)
			y = data_interface.get("y^", j=j, rho=rho, l=l)

			if l > 0:
				y_prev = data_interface.get("y^", j=j, rho=rho, l=l - 1)
			else:
				y_prev = 0

			n_nodes = schema.get_index_bound("j")
			x_out = list(map(lambda i: x_processed_or_zero(j=j, i=i, rho=rho, l=l), range(n_nodes)))
			x_in = list(map(lambda i: x_processed_or_zero(j=i, i=j, rho=rho, l=l), range(n_nodes)))
			generic.Log.debug("j rho l", j, rho, l, "x_eq", x_eq, "y^", y, "y_prev^", y_prev, "g^",
							  g, "z^", z, "x_out^", sum(x_out), "x_in^", sum(x_in))
			balance = y - y_prev + z + g + sum(x_out) - sum(x_in)
			generic.Log.debug("x_eq", x_eq, "balance", balance)
			self.assertTrue(math.isclose(x_eq, balance, abs_tol=0.1))

	def test_transfer_op(self):
		sim_global = sml.SimGlobal()
		proc_intensity_upper = self.env.data_interface.get("mm_psi", j=0, l=0, i=1)
		proc_intensity_fraction = self.env.data_interface.get("m_psi", j=0, l=0, i=1, rho=0)
		transfer = sml.TransferOp(sim_global=sim_global,
			indices_planned_plain=self.env.schema.indices_dict_to_plain("x", j=0, i=1, l=0, rho=0),
			amount_planned=proc_intensity_fraction * proc_intensity_upper * 1000,
			proc_intensity_fraction=proc_intensity_fraction,
			proc_intensity_upper=proc_intensity_upper,
			proc_intensity_lower=0,
			val_l=0,
			proc_noise_type="gauss")
		container = sml.Container()
		container_output = sml.Container()
		transfer.set_container_input(container)
		transfer.set_container_output(container_output)
		chunk = proc_intensity_upper * proc_intensity_fraction * 2
		self.assertTrue(math.isclose(container.amount, 0, abs_tol=0.001))
		self.assertTrue(math.isclose(container_output.amount, 0, abs_tol=0.001))

		for i in range(5):
			container.amount = chunk
			transfer.step()
			transfer.step_teardown()

		self.assertTrue(transfer.amount_processed > 0)
		self.assertTrue(container_output.amount > 0)

	def test_store_op(self):
		sim_global = sml.SimGlobal()
		intensity_upper=3.0
		container_input = sml.Container()
		amount_planned=6  # Plain is not fullfilled
		store_op = sml.StoreOp(sim_global=sim_global,
			indices_planned_plain=self.env.schema.indices_dict_to_plain("y", j=0, rho=0, l=0),
			amount_planned=amount_planned, proc_intensity_upper=intensity_upper, proc_intensity_lower=-intensity_upper,
			val_l=0,
			proc_intensity_fraction=1.0, container_input=container_input, container_processed=sml.Container())

		for i in range(3):
			container_input.amount = intensity_upper
			store_op.step()
			store_op.step_teardown()
			container_input.amount = 0

		self.assertTrue(math.isclose(amount_planned, store_op.amount_processed, abs_tol=0.00001))
		amount_processed_initial = 10
		store_op.amount_processed = amount_processed_initial  # Plan is exceeded

		for i in range(3):
			container_input.amount = intensity_upper / 2
			store_op.step()
			container_input.amount /= 2
			store_op.step_teardown()
			container_input.amount = 0

		self.assertTrue(amount_planned <= store_op.amount_processed < amount_processed_initial)

	def test_generate_op(self):
		n_steps = 3
		intensity = 4.0
		op = sml.GenerateOp(sim_global=sml.SimGlobal(), indices_planned_plain=(0, 0, 0),
			amount_planned=n_steps * intensity, proc_intensity_fraction=1.0, proc_intensity_upper=intensity, val_l=0)

		for _ in range(n_steps):
			op.step()

		self.assertTrue(math.isclose(intensity * n_steps, op.amount_processed))

	def test_init(self):
		s = sml.Simulation(env=self.env)
		self.assertTrue(len(list(self.env.schema.radix_map_iter("j", "rho", "l"))) > 0)
		self.assertEqual(len(s.containers), len(list(self.env.schema.radix_map_iter("j", "rho", "l"))))
		self.assertEqual(len(s.containers_processed), len(list(self.env.schema.radix_map_iter("j", "rho"))))
		# self.assertEqual(len(s.transfer_ops), len(list(self.env.schema.radix_map_iter("j", "i", "rho", "l"))))  # Wrong, because self-connected and zero-throughput channels are optimized out
		self.assertEqual(len(s.drop_ops), len(list(self.env.schema.radix_map_iter("j", "rho", "l"))))
		self.assertEqual(len(s.process_ops), len(list(self.env.schema.radix_map_iter("j", "rho", "l"))))
		self.assertEqual(len(s.store_ops), len(list(self.env.schema.radix_map_iter("j", "rho", "l"))))
		self.assertTrue(len(s.drop_ops) > 0)

		self.assertTrue(not (s.process_ops[(0, 0, 0)].container_input is s.process_ops[(0, 1, 0)].container_input))
		self.assertTrue(not (s.generate_ops[(0, 0, 0)].container_input is s.process_ops[(0, 1, 0)].container_input))

		for j, rho, l in self.env.schema.radix_map_iter("j", "rho", "l"):
			ind = tuple([j, rho, l])
			self.assertTrue(s.containers[ind] is s.generate_ops[ind].container_input)
			self.assertTrue(s.containers[ind] is s.process_ops[ind].container_input)
			self.assertTrue(s.containers[ind] is s.store_ops[ind].container_input)
			self.assertTrue(s.containers[ind] is s.drop_ops[ind].container_input)

			for i in range(self.env.schema.get_index_bound("i")):
				if s.helper_virt.indices_transfer_is_connected((j, i, rho, l,)):
					self.assertTrue(s.containers[ind] is s.transfer_ops[(j, i, rho, l)].container_input)
					self.assertTrue(s.containers[(i, rho, l,)] is s.transfer_ops[(j, i, rho, l)].container_output)

	def test_simulation(self):
		s = sml.Simulation(env=self.env)
		s.run()

		for op in s.ops_all():
			log.info("test_simulation", "op name:", op.as_str_short(), "amount processed:", op.amount_processed,
				"amount planned", op.amount_planned)


if __name__ == "__main__":
	unittest.main()
