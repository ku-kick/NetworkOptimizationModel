"""

Optimizes a network's plan and parameters using 2 models: simulation +
GA-based parameters optimizer, and the linear programming-based information
process technology synthesizer. After a set of iterations, the two procedures
converge (unproven).

The reasoning behind the expected converging is that on each iteration, the
optimizer produces a better version of the technology + parameters than on
the previous one. Sure, there is a possibility that with a new plan or
parameters we just shoot ourselves in the leg, setting the entire optimization
for a failure.

"""

import twoopt.data_processing.data_processor

class Orchestrated2StageSolver(
        twoopt.data_processing.data_processor.Solver)

    def __init__(self, data_provider):
        from twoopt.optimization.data_amount_planning import \
            make_data_interface_schema_helper

        # Initialize superclasses
        data_interface, schema = make_data_interface_schema_helper(
            data_provider=self._data_provider)
        twoopt.data_processing.data_processor.Solver.__init__(self,
            data_interface)

        self._data_provider = data_provider
        self._schema = schema

    def run(self):
        from twoopt.data_processing.data_provider import RamDataProvider
        from twoopt.optimization.ga_network_optimization import \
            GaNetworkOptimizationSolver
        from twoopt.optimization.data_amount_planning import \
            ProcessedDataAmountMaximizationSolver

        # Initialize temporary storages. 2 storages for each solver
        ga_network_optimization_data_provider = RamDataProvider()
        ga_network_optimization_data_provider.set_data_from_data_provider(
            self._data_provider)
        data_amount_planning_data_provider = RamDataProvider()
        data_amount_planning_data_provider.set_data_from_data_provider(
            self._data_provider)

        # Get the number of iterations
        n_iterations = self.get_data_interface().data("twoopt_n_iterations")

        # Start the recursive 2-stage optimization procedure
        for i in range(n_iterations):
            # Create and run the first solver
            data_amount_planning_solver = ProcessedDataAmountMaximizationSolver(
                data_provider=data_amount_planning_data_provider)
            data_amount_planning_solver.run()

            # Copy the results
            ga_network_optimization_data_provider.set_data_from_data_provider(
                data_amount_planning_data_provider)

            # Create and run the second solver
            ga_network_optimization_solver = GaNetworkOptimizationSolver(
                data_provider=ga_network_optimization_data_provider)
            ga_network_optimization_solver.run()

            # Copy the results
            data_amount_planning_data_provider.set_data_from_data_provider(
                ga_network_optimization_data_provider)

        # Copy the data from the 1st solver's data provider
        self._data_provider.set_data_from_data_provider(
            data_amount_planning_data_provider)
