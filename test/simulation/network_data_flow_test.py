import pathlib
import twoopt.data_processing.data_provider
import twoopt.simulation.network_data_flow
import unittest


_THIS_PATH = pathlib.Path(__file__).resolve().parent


class Test(unittest.TestCase):

    def test_ushakov_simulation(self):
        data_provider = twoopt.data_processing.data_provider\
            .PermissiveCsvBufferedDataProvider(
            csv_file_name=str(_THIS_PATH / "network_data_flow_test" / "ushakov.csv"))  # Network from "Ushakov, 2021"
        simulation = twoopt.simulation.network_data_flow.NetworkDataFlow(
            data_provider=data_provider)
        simulation.run()


if __name__ == "__main__":
    unittest.main()
