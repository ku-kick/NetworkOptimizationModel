import pathlib
import twoopt.data_processing.data_provider
import twoopt.optimization.orchestrated_two_stage_optimization
import unittest


_THIS_PATH = pathlib.Path(__file__).resolve().parent


class GaNetworkOptimizationTest(unittest.TestCase):
    def test_run(self):
        data_provider = twoopt.data_processing.data_provider \
            .PermissiveCsvBufferedDataProvider(
            csv_file_name=str( _THIS_PATH / "ga_network_optimization_test" \
            / "ushakov.csv"))  # Network from "Ushakov, 2021"
        solver = twoopt.optimization.orchestrated_two_stage_optimization\
            .Orchestrated2StageSolver(data_provider=data_provider)
        solver.run()
        data_provider.sync()


if __name__ == "__main__":
    unittest.main()
