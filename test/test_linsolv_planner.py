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


class TestLinsolvPlanner(unittest.TestCase):
	DATA_FILE_CSV = str(pathlib.Path(__file__).parent / "test_linsolv_planner_output_data.csv")
	SCHEMA_FILE_JSON = str(pathlib.Path(__file__).parent / "test_schema_3.json")

	def setUp(self) -> None:
		psi_upper = 10
		phi_upper = 10
		v_upper = 10
		x_eq_upper = 10

		if not os.path.exists(TestLinsolvPlanner.DATA_FILE_CSV):
			cli.generate_random(TestLinsolvPlanner.SCHEMA_FILE_JSON, psi_upper, phi_upper, v_upper, x_eq_upper,
				TestLinsolvPlanner.DATA_FILE_CSV)

		self.data_provider = linsmat.PermissiveCsvBufferedDataProvider(csv_file_name=TestLinsolvPlanner.DATA_FILE_CSV)
		self.schema = linsmat.Schema(filename=TestLinsolvPlanner.SCHEMA_FILE_JSON)
		self.data_interface = linsmat.DataInterface(self.data_provider, self.schema)

	def tearDown(self) -> None:
		os.remove(TestLinsolvPlanner.DATA_FILE_CSV)

	def test_init(self):

		ls_planner = linsolv_planner.LinsolvPlanner(self.data_interface, self.schema)
		self.assertTrue(self.schema.get_max_dec_from_indices("j", "rho", "l") == len(ls_planner.eq_lhs))
		self.assertTrue(any(map(lambda i: len(i) == ls_planner.row_index.get_row_len(), ls_planner.eq_lhs)))
		self.assertTrue(len(ls_planner.eq_lhs) == len(ls_planner.eq_rhs))
		self.assertTrue(len(ls_planner.bnd) == ls_planner.row_index.get_row_len())

	def test_solve(self):
		ls_planner = linsolv_planner.LinsolvPlanner(self.data_interface, self.schema)
		res = ls_planner.solve()
		print(cli.Format.numpy_result(res, self.schema))
		res_x = res.x
		row_index = ls_planner.row_index
		assert ["j", "rho", "l"] == ls_planner.schema.get_var_indices("x_eq")

		for count, indices in enumerate(ut.radix_cartesian_product(ls_planner.schema.get_var_radix("x_eq"))):
			j, rho, l = indices
			sm = functools.reduce(lambda acc, i: acc + res_x[row_index.get_pos("x", j=i, i=j, l=l, rho=rho)]
				- res_x[row_index.get_pos("x", j=j, i=i, l=l, rho=rho)], range(ls_planner.schema.get_index_bound("i")),
				0)
			sm += res_x[row_index.get_pos("y", j=j, rho=rho, l=l)]

			if l > 0:
				sm -= res_x[row_index.get_pos("y", j=j, rho=rho, l=l-1)]

			sm += res_x[row_index.get_pos("z", j=j, rho=rho, l=l)]
			sm += res_x[row_index.get_pos("g", j=j, rho=rho, l=l)]
			x_eq = ls_planner.eq_rhs[count]
			Log.debug("indices", j, rho, l, "x_eq", x_eq, "sm", sm)
			self.assertTrue(math.isclose(sm, x_eq, abs_tol=.001))


unittest.main()
