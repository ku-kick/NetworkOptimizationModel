import pathlib
import twoopt.data_processing.data_provider
import twoopt.optimization.ga_network_optimization
import unittest


_THIS_PATH = pathlib.Path(__file__).resolve().parent


def _data_provider_init_ga_configs(data_provider):
    values = {
        "OPT_VIRT_GA_POPULATION_SIZE" : 3,
        "OPT_VIRT_GA_SWAP_PERC_POPULATION" : 1.0,  # Fraction of individuals from the entire population that will be selected for crossing,
        "OPT_VIRT_GA_REMOVE_PERC_POPULATION" : .6,  # % of population to be removed,
        "OPT_VIRT_GA_N_ITERATIONS" : 2,
        "OPT_VIRT_GA_N_ITERATIONS" : 2,
        "OPT_VIRT_ORCHESTRATION_N_ITERATIONS" : 2,
    }

    for k, v in values:
        data_provider.set_data(v, k)

    return data_provider


class GaNetworkOptimizationTest(unittest.TestCase):
    def test_run(self):
        data_provider = twoopt.data_processing.data_provider \
            .PermissiveCsvBufferedDataProvider(
            csv_file_name=str( _THIS_PATH / "ga_network_optimization_test" \
            / "ushakov.csv"))  # Network from "Ushakov, 2021"
        data_provider = _data_provider_init_ga_configs(data_provider)
        ga_network_optimization_solver = twoopt.optimization \
            .ga_network_optimization.GaNetworkOptimizationSolver(
            data_provider=data_provider)
        ga_network_optimization_solver.run()
        data_provider.sync()


if __name__ == "__main__":
    unittest.main()
