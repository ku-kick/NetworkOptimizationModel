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

        # Initialize `SimulationBasedSolver`
        data_interface, _ = make_data_interface_schema_helper(
            data_provider)
        simulation = NetworkDataFlow(data_provider=data_provider)
        twoopt.data_processing.data_processor.SimulationBasedSolver.__init__(
            self, data_interface=data_interface, simulation=simulation)

        # Initialize the legacy GA-based optimizer
        virt_helper = data_amount_planning_make_legacy_virt_helper(
            data_provider)
        twoopt.sim_opt.GaSimVirtOpt.__init__(
            self,
            simulation_constructor=self._simulation_constructor_legacy,
            virt_helper=virt_helper)

        self._data_provider = data_provider

    def run(self):
        legacy_data_interface = twoopt.sim_opt.GaSimVirtOpt.run(self)

        # Dump the results into the storage
        self._data_provider.set_data_from_data_provider(
            legacy_data_interface.data_provider())
