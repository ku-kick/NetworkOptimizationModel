import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
import config
config.cfg_set_test()
from twoopt import cli, linsmat, ut, linsolv_planner
import functools
import os
import math
from generic import Log
import logging
import ut
import sim_opt
import simulation
import copy
import orchestration
import config


log = ut.Log(file=__file__, level=ut.Log.LEVEL_VERBOSE)


class TestSimOpt(unittest.TestCase):
	def test_construction(self):
		# Prepare the data
		data_file_csv = str(pathlib.Path(__file__).parent / "ushakov.csv")
		schema_file_json = str(pathlib.Path(__file__).parent / "ushakov.json")
		virt_opt = orchestration.VirtOpt(schema_path=schema_file_json, storage_path=data_file_csv)

	def test_optimization(self):
		config.cfg_set_test()
		data_file_csv = str(pathlib.Path(__file__).parent / "ushakov.csv")
		schema_file_json = str(pathlib.Path(__file__).parent / "ushakov.json")
		virt_opt = orchestration.VirtOpt(schema_path=schema_file_json, storage_path=data_file_csv)
		virt_opt.run()

if __name__ == "__main__":
	unittest.main()
