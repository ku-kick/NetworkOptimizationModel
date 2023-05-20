"""

Performs load balancing in a virtualized network. Complementary to
`data_amount_planning`.

"""

import twoopt.data_processing.data_processor
import twoopt.sim_opt


class GaNetworkOptimizationSolver(
        twoopt.data_processing.data_processor.SimulationBasedSolver,
        twoopt.sim_opt.GaSimVirtOpt):

    def _simulation_constructor_legacy(self, *args, **kwargs):
        """
        Legacy-compatible adapter
        """
        return self.simulation()

    def __init__(self, data_provider):

        from twoopt.data_processing.legacy_etl import \
            data_amount_planning_make_legacy_virt_helper
        from twoopt.optimization.data_amount_planning import \
            make_data_interface_schema_helper
        from twoopt.simulation.network_data_flow import NetworkDataFlow
        from twoopt.data_processing.data_interface import GetattrDataInterface

        # Initialize `SimulationBasedSolver`
        data_interface, schema = make_data_interface_schema_helper(
            data_provider)

        # Extend the commonly used schema
        variable_index_pairs = {
            "OPT_VIRT_GA_POPULATION_SIZE" : [],
            "OPT_VIRT_GA_SWAP_PERC_POPULATION" : [],  # Fraction of individuals from the entire population that will be selected for crossing,
            "OPT_VIRT_GA_REMOVE_PERC_POPULATION" : [],  # % of population to be removed,
            "OPT_VIRT_GA_N_ITERATIONS" : [],
            "OPT_VIRT_ORCHESTRATION_N_ITERATIONS" : [],
        }

        for k, v in variable_index_pairs.items():
            schema.set_variable_indices(**{k: v})

        simulation = NetworkDataFlow(data_provider=data_provider)
        twoopt.data_processing.data_processor.SimulationBasedSolver.__init__(
            self, data_interface=data_interface, simulation=simulation)

        # Initialize the legacy GA-based optimizer
        virt_helper = data_amount_planning_make_legacy_virt_helper(
            data_provider)
        twoopt.sim_opt.GaSimVirtOpt.__init__(
            self,
            simulation_constructor=self._simulation_constructor_legacy,
            virt_helper=virt_helper,
            config=GetattrDataInterface(data_interface))

        self._data_provider = data_provider

    def run(self):
        legacy_data_interface = twoopt.sim_opt.GaSimVirtOpt.run(self)

        # Dump the results into the storage
        self._data_provider.set_data_from_data_provider(
            legacy_data_interface.data_provider())
