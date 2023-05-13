import pathlib
import twoopt.data_processing.data_provider
import twoopt.optimization.ga_network_optimization
import unittest


_THIS_PATH = pathlib.Path(__file__).resolve().parent


class GaNetworkOptimizationTest(unittest.TestCase):
    def test_run(self):
        data_provider = twoopt.data_processing.data_provider \
            .PermissiveCsvBufferedDataProvider(
            csv_file_name=str( _THIS_PATH / "ga_network_optimization_test" \
            / "ushakov.csv"))  # Network from "Ushakov, 2021"
        ga_network_optimization_solver = twoopt.optimization \
            .ga_network_optimization.GaNetworkOptimizationSolver(
            data_provider=data_provider)
        ga_network_optimization_solver.run()


if __name__ == "__main__":
    unittest.main()
