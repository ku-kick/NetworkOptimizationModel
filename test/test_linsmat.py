import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import linsmat
import os


class TestIndex(unittest.TestCase):

	def test_post_init(self):
		ind = linsmat.RowIndex(indices=dict(j=2, rho=3), variables=dict(x=['j', 'rho'], y=['j']))

	def test_to_mixed_radix_num(self):
		ind = linsmat.RowIndex(indices=dict(a=3, b=5), variables=dict(x=['a'], y=['a', 'b']))

	def test_get_pos(self):
		ind = linsmat.RowIndex(indices=dict(a=3, b=5), variables=dict(x=['a'], y=['a', 'b'], z=['a', 'b']))
		print(ind.get_pos('y', a=2, b=4))
		print(ind.get_pos('x', a=2))
		print(ind.radix_maps)
		print(ind.radix_mult_vectors)
		print(linsmat.RowIndex(indices=dict(a=3), variables=dict(x=['a'])).get_pos('x', a=2))


class TestSchema(unittest.TestCase):

	def setUp(self) -> None:
		unittest.TestCase.setUp(self)

		with open('test.json', 'w') as f:
			f.write('''
				{
					"variableindices": {
						"x": ["j", "i"],
						"y": ["m"]
					},
					"indexbound": {
						"j": 2,
						"i": 3,
						"m": 4
					}
				}
			''')

	def tearDown(self) -> None:
		super().tearDown()
		os.remove("test.json")

	def test_get_var_radix(self):
		schema = linsmat.Schema()
		schema.read("test.json")
		self.assertEqual([2, 3], schema.get_var_radix("x"))
		self.assertEqual([4], schema.get_var_radix("y"))


unittest.main()
