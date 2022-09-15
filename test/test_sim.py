import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import linsmat
import os
import pathlib
import math


class TestData(unittest.TestCase):
	__HERE = pathlib.Path(os.path.realpath(__file__)).parent
	#TODO implement test run and produce a trace output (see Simulation.Trace)


unittest.main()
