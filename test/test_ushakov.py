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


log = ut.Log(file=__file__, level=ut.Log.LEVEL_VERBOSE)


class TestUshakov(unittest.TestCase):
	DATA_FILE_CSV = str(pathlib.Path(__file__).parent / "ushakov.csv")
	SCHEMA_FILE_JSON = str(pathlib.Path(__file__).parent / "ushakov.json")

	def setUp(self) -> None:
		Log.LEVEL = Log.LEVEL_DEBUG
		self.schema = linsmat.Schema(filename=TestUshakov.SCHEMA_FILE_JSON)
		self.data_provider = linsmat.PermissiveCsvBufferedDataProvider(csv_file_name=TestUshakov.DATA_FILE_CSV)
		self.data_interface = linsmat.ZeroingDataInterface(self.data_provider, self.schema)

	def test_solve(self):
		ls_planner = linsolv_planner.LinsolvPlanner(self.data_interface, self.schema)
		res = ls_planner.solve()
		log.info(cli.Format.numpy_result(res, ls_planner.schema))


if __name__ == "__main__":
	unittest.main()
