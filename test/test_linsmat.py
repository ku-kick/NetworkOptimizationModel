import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from twoopt import linsmat


class TestArgs(unittest.TestCase):

	def test_post_init(self):
		ind = linsmat.RowIndex(indices=dict(j=2, rho=3), variables=dict(x=['j', 'rho'], y=['j']))
		print(ind.radix_map)


unittest.main()
