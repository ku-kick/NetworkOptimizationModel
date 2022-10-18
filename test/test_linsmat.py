"""
Tests classes from `linsmat`, and ETL-related functionality from other modules.
"""

import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import linsmat
import ut
import linsolv_planner
import os
import pathlib
import math
import sim_opt
import cli

log = ut.Log(file=__file__, level=ut.Log.LEVEL_VERBOSE)


class TestIndex(unittest.TestCase):

	def test_post_init(self):
		ind = linsmat.RowIndex(indices=dict(j=2, rho=3), variables=dict(x=['j', 'rho'], y=['j']))

	def test_to_mixed_radix_num(self):
		ind = linsmat.RowIndex(indices=dict(a=3, b=5), variables=dict(x=['a'], y=['a', 'b']))

	def test_get_pos(self):
		ind = linsmat.RowIndex(indices=dict(a=3, b=5), variables=dict(x=['a'], y=['a', 'b'], z=['a', 'b'], k=[], m=[]))
		print(ind.get_pos('y', a=2, b=4))
		print(ind.get_pos('x', a=2))
		print(ind.radix_maps)
		print(ind.radix_mult_vectors)
		print(linsmat.RowIndex(indices=dict(a=3), variables=dict(x=['a'])).get_pos('x', a=2))
		self.assertTrue(ind.get_row_len() == 3 + 3 * 5 + 3 * 5 + 1 + 1)  # Pardon my french, but this form of writing it makes direct intuitive mapping to the structure of the variable set

	def test_no_indices(self):
		ind = linsmat.RowIndex(indices=dict(), variables=dict(m=[], k=[]))
		self.assertTrue(ind.get_pos('m') in [0, 1])
		self.assertTrue(ind.get_pos('k') in [0, 1])
		self.assertTrue(ind.get_pos('m') != ind.get_pos('k'))


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



class TestData(unittest.TestCase):
	__HERE = pathlib.Path(os.path.realpath(__file__)).parent

	def test_load(self):
		schema=linsmat.Schema("her")
		data_interface = linsmat.DataInterface(
			provider=linsmat.PermissiveCsvBufferedDataProvider(str(TestData.__HERE / "test_data.csv")),
			schema=linsmat.Schema(filename=str(TestData.__HERE / "test_schema.json")))
		self.assertTrue(math.isclose(1.1, data_interface.get("x", **{"a": 1, "b": 2, "c": 3})))
		self.assertTrue(math.isclose(3.2, data_interface.get("x", **{"b": 2, "a": 1, "c": 2})))
		self.assertTrue(math.isclose(3.0, data_interface.get("y", **{"c": 3, "a": 2})))

	def test_dict_ram_data_provider_clone(self):
		schema=linsmat.Schema("her")
		data_interface = linsmat.DataInterface(
			provider=linsmat.PermissiveCsvBufferedDataProvider(str(TestData.__HERE / "test_data.csv")),
			schema=linsmat.Schema(filename=str(TestData.__HERE / "test_schema.json")))

		# Clone data into RAM
		dict_ram_data_interface = data_interface.clone_as_dict_ram()

		# Change a value, and make sure that the changes have not been reflected in the data file
		val_prev = data_interface.get("x", **{"b": 2, "a": 1, "c": 2})
		dict_ram_data_interface.set("x", val_prev + 10.0, a=1, b=2, c=2)
		del data_interface
		data_interface = linsmat.DataInterface(
			provider=linsmat.PermissiveCsvBufferedDataProvider(str(TestData.__HERE / "test_data.csv")),
			schema=linsmat.Schema(filename=str(TestData.__HERE / "test_schema.json")))
		self.assertTrue(math.isclose(data_interface.get("x", **{"b": 2, "a": 1, "c": 2}), val_prev))
		self.assertFalse(math.isclose(dict_ram_data_interface.get("x", **{"b": 2, "a": 1, "c": 2}), val_prev))

	def test_indexing_simple(self):
		data_provider = linsmat.PermissiveCsvBufferedDataProvider(
			csv_file_name=ut.module_file_get_abspath(__file__, "test_solve_transfer_simple.csv"))
		schema = linsmat.Schema(filename=ut.module_file_get_abspath(__file__, "test_solve_transfer_simple.json"))
		data_interface = linsmat.ZeroingDataInterface(data_provider, schema)
		planner = linsolv_planner.LinsolvPlanner(data_interface, schema)

		pos_psi_1_0_0_0 = planner.row_index.get_pos("x", j=1, i=0, rho=0, l=0)
		pos_psi_0_1_0_0 = planner.row_index.get_pos("x", j=0, i=1, rho=0, l=0)
		psi_1_0_0_0 = planner.bnd[pos_psi_1_0_0_0]
		psi_0_1_0_0 = planner.bnd[pos_psi_0_1_0_0]
		self.assertTrue(math.isclose(psi_0_1_0_0[1], 10000.0))


class TestGaGeneVirt(unittest.TestCase):
	"""
	GA-based simulation parameters' optimizer uses GA as its optimization
	algorithm. GaGeneVirt is a gene representation that provides
	inteoperpability w/ ETL-related classes from `linsmat` module (w/
	DataInterface in particular).
	"""

	__CSV_OUTPUT_FILE = ut.file_here_to_str_path(__file__, "test_linsmat_ga_gene_virt.csv")
	__SCHEMA_FILE = ut.file_here_to_str_path(__file__, "test_schema_3.json")

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
				output=self.__CSV_OUTPUT_FILE
			)
		self.env = linsmat.Env.make_from_file(schema_file=self.__SCHEMA_FILE, storage_file=self.__CSV_OUTPUT_FILE,
			row_index_variables=[])
		self.env.data_interface = linsmat.ZeroingDataInterface(provider=self.env.data_interface.provider, schema=self.env.schema)  # Some values like those pertaining to loop channes are not present in the generated file

	def test_construct_compare(self):
		"""
		Construct a gene from a DataInterface instance and backwards. Make sure
		that the instances of DataInterface do not share the same mem.
		"""
		helper_virt = linsmat.HelperVirt(env=self.env)
		ga_gene = sim_opt.GaGeneVirt.new_from_helper_virt(helper_virt)
		data_interface = ga_gene.as_data_interface(helper_virt)
		data_interface.set(helper_virt.var_transfer_intensity_fraction, 42.0, j=0, rho=0, l=0)
		original_val = self.env.data_interface.get(helper_virt.var_transfer_intensity_fraction, j=0, rho=0, l=0)
		changed_val = data_interface.get(helper_virt.var_transfer_intensity_fraction, j=0, rho=0, l=0)
		self.assertFalse(math.isclose(original_val, changed_val))


unittest.main()
