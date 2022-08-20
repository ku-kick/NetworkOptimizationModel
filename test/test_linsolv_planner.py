import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import cli, linsmat, ut, linsolv_planner
import os


class TestLinsolvPlanner(unittest.TestCase):
	DATA_FILE_CSV = str(pathlib.Path(__file__).parent / "test_linsolv_planner_output_data.csv")
	SCHEMA_FILE_JSON = str(pathlib.Path(__file__).parent / "test_schema_3.json")

	def setUp(self) -> None:
		psi_upper = 10
		phi_upper = 10
		v_upper = 10
		x_eq_upper = 10
		cli.generate_random(TestLinsolvPlanner.SCHEMA_FILE_JSON, psi_upper, phi_upper, v_upper, x_eq_upper,
			TestLinsolvPlanner.DATA_FILE_CSV)

	def tearDown(self) -> None:
		os.remove(TestLinsolvPlanner.DATA_FILE_CSV)

	def test_init(self):
		data_provider = linsmat.PermissiveCsvBufferedDataProvider(csv_file_name=TestLinsolvPlanner.DATA_FILE_CSV)
		schema = linsmat.Schema(filename=TestLinsolvPlanner.SCHEMA_FILE_JSON)
		data_interface = linsmat.DataInterface(data_provider, schema)
		ls_planner = linsolv_planner.LinsolvPlanner(data_interface, schema)
		self.assertTrue(schema.get_max_dec_from_indices("j", "rho", "l") == len(ls_planner.eq_lhs))
		self.assertTrue(any(map(lambda i: len(i) == ls_planner.row_index.get_row_len(), ls_planner.eq_lhs)))
		self.assertTrue(len(ls_planner.eq_lhs) == len(ls_planner.eq_rhs))
		self.assertTrue(len(ls_planner.bnd) == ls_planner.row_index.get_row_len())


unittest.main()
