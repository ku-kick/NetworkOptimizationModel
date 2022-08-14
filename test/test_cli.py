import unittest
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / 'twoopt'))
from twoopt import cli, linsmat, ut
import pathlib


class TestRandomGenerator(unittest.TestCase):

	def test_generate_random(self):
		schema_file = "test_schema_2.json"
		psi_upper = 10
		phi_upper = 10
		v_upper = 10
		output="output_data.csv"
		cli.generate_random(schema_file, psi_upper, phi_upper, v_upper, output)
		data_provider = linsmat.PermissiveCsvBufferedDataProvider(output)
		schema = linsmat.Schema(None, schema_file)
		data_interface = linsmat.DataInterface(data_provider, schema)

		for var in ["psi", "phi", "v"]:
			radix_base = schema.get_var_radix(var)

			for mixed_radix_index in ut.radix_cartesian_product(radix_base):
				dict_mixed_radix_index = schema.indices_plain_to_dict(var, *mixed_radix_index)[1]
				data_interface.get(var, **dict_mixed_radix_index)  # Checks whether the requested data is in the provided csv. If no assertion is raised, everything has gone smooth


unittest.main()
