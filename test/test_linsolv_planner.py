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


class TestLinsolvPlanner(unittest.TestCase):
	DATA_FILE_CSV = str(pathlib.Path(__file__).parent / "test_linsolv_planner_output_data.csv")
	SCHEMA_FILE_JSON = str(pathlib.Path(__file__).parent / "test_schema_3.json")

	def setUp(self) -> None:
		psi_upper = 10
		phi_upper = 10
		v_upper = 10
		x_eq_upper = 10
		tl_upper = 3000
		mm_psi_upper = psi_upper / tl_upper
		mm_phi_upper = phi_upper / tl_upper
		mm_v_upper = v_upper / tl_upper
		Log.LEVEL = Log.LEVEL_DEBUG
		self.schema = linsmat.Schema(filename=TestLinsolvPlanner.SCHEMA_FILE_JSON)
		entry_nodes = list(map(lambda rho: dict(j=0, l=0, rho=rho), range(self.schema.get_index_bound("rho"))))

		if not os.path.exists(TestLinsolvPlanner.DATA_FILE_CSV):
			cli.generate_random(
				schema=TestLinsolvPlanner.SCHEMA_FILE_JSON,
				psi_upper=psi_upper,
				phi_upper=phi_upper,
				v_upper=v_upper,
				x_eq_upper=x_eq_upper,
				mm_psi_upper=mm_psi_upper,
				mm_phi_upper=mm_phi_upper,
				mm_v_upper=mm_v_upper,
				tl_upper=tl_upper,
				entry_nodes=entry_nodes,
				output=self.DATA_FILE_CSV
			)

		self.data_provider = linsmat.PermissiveCsvBufferedDataProvider(csv_file_name=TestLinsolvPlanner.DATA_FILE_CSV)
		self.data_interface = linsmat.DataInterface(self.data_provider, self.schema)

	def tearDown(self) -> None:
		os.remove(TestLinsolvPlanner.DATA_FILE_CSV)

	def test_init(self):

		ls_planner = linsolv_planner.LinsolvPlanner(self.data_interface, self.schema)
		self.assertTrue(any(map(lambda i: len(i) == ls_planner.row_index.get_row_len(), ls_planner.eq_lhs)))
		self.assertTrue(len(ls_planner.eq_lhs) == len(ls_planner.eq_rhs))
		self.assertTrue(len(ls_planner.bnd) == ls_planner.row_index.get_row_len())

	def test_solve(self):
		ls_planner = linsolv_planner.LinsolvPlanner(self.data_interface, self.schema)
		res = ls_planner.solve()
		Log.debug(cli.Format.numpy_result(res, ls_planner.schema))
		res_x = res.x

		self.assertTrue(res_x is not None)

		Log.debug(TestLinsolvPlanner.test_solve, "res_x\n", res_x)
		row_index = ls_planner.row_index
		Log.debug(row_index.get_pos('z', j=0, rho=0, l=0))
		assert ["j", "rho", "l"] == ls_planner.schema.get_var_indices("x_eq")

		count = 0
		for indices in ut.radix_cartesian_product(ls_planner.schema.get_var_radix("x_eq")):
			try:
				ls_planner.data_interface.get_plain("x_eq", *indices)
			except AssertionError:
				continue

			j, rho, l = indices
			sm = functools.reduce(lambda acc, i: acc - res_x[row_index.get_pos("x", j=i, i=j, l=l, rho=rho)]
				+ res_x[row_index.get_pos("x", j=j, i=i, l=l, rho=rho)], range(ls_planner.schema.get_index_bound("i")),
				0)
			sm += res_x[row_index.get_pos("y", j=j, rho=rho, l=l)]

			if l > 0:
				sm -= res_x[row_index.get_pos("y", j=j, rho=rho, l=l-1)]

			sm += res_x[row_index.get_pos("z", j=j, rho=rho, l=l)]
			sm += res_x[row_index.get_pos("g", j=j, rho=rho, l=l)]
			x_eq = ls_planner.eq_rhs[count]
			Log.debug("indices", j, rho, l, "x_eq", x_eq, "sm", sm)
			self.assertTrue(math.isclose(sm, x_eq, abs_tol=.001))
			count += 1


class TestInfluxConstraintLp:
	def setUp(self) -> None:
		psi_upper = 10
		phi_upper = 10
		v_upper = 10
		x_eq_upper = 10
		tl_upper = 3000
		mm_psi_upper = psi_upper / tl_upper
		mm_phi_upper = phi_upper / tl_upper
		mm_v_upper = v_upper / tl_upper

		Log.set_level(logging.DEBUG)

		if not os.path.exists(TestLinsolvPlanner.DATA_FILE_CSV):
			cli.generate_random(
				schema=TestLinsolvPlanner.SCHEMA_FILE_JSON,
				psi_upper=psi_upper,
				phi_upper=phi_upper,
				v_upper=v_upper,
				x_eq_upper=x_eq_upper,
				mm_psi_upper=mm_psi_upper,
				mm_phi_upper=mm_phi_upper,
				mm_v_upper=mm_v_upper,
				tl_upper=tl_upper,
				output=self.DATA_FILE_CSV
			)

		self.data_provider = linsmat.PermissiveCsvBufferedDataProvider(csv_file_name=TestLinsolvPlanner.DATA_FILE_CSV)
		self.schema = linsmat.Schema(filename=TestLinsolvPlanner.SCHEMA_FILE_JSON)
		self.data_interface = linsmat.DataInterface(self.data_provider, self.schema)

	def test_solve(self):
		planner = linsolv_planner.InfluxConstraintLp(data_interface=self.data_interface, schema=self.schema)
		res = planner.solve()
		Log.info(TestInfluxConstraintLp.test_solve, res.x)
		Log.info(TestInfluxConstraintLp.test_solve, cli.Format.numpy_result(res, planner.schema))
		res_x = res.x
		row_index = planner.row_index
		count = 0

		for indices in ut.radix_cartesian_product(planner.schema.get_var_radix("x_eq")):
			Log.debug(TestInfluxConstraintLp.test_solve, "indices", indices)
			try:
				planner.data_interface.get_plain("x_eq", *indices)
			except AssertionError:
				continue

			j, rho, l = indices
			sm = functools.reduce(lambda acc, i: acc - res_x[row_index.get_pos("x", j=i, i=j, l=l, rho=rho)]
				+ res_x[row_index.get_pos("x", j=j, i=i, l=l, rho=rho)], range(planner.schema.get_index_bound("i")),
				0)
			sm += res_x[row_index.get_pos("y", j=j, rho=rho, l=l)]

			if l > 0:
				sm -= res_x[row_index.get_pos("y", j=j, rho=rho, l=l-1)]

			sm += res_x[row_index.get_pos("z", j=j, rho=rho, l=l)]
			sm += res_x[row_index.get_pos("g", j=j, rho=rho, l=l)]
			x_eq = planner.eq_rhs[count]
			Log.debug("indices", j, rho, l, "x_eq", x_eq, "sm", sm)
			self.assertTrue(math.isclose(sm, x_eq, abs_tol=.001))
			count += 1


if __name__ == "__main__":
	unittest.main()
