import dataclasses
import twoopt


class ProcessedDataAmountMaximizationDataInterface(twoopt.data_processing.data_interface.ConstrainedDataInterface):
    def __init__(self, data_interface_implementor):
        data_format = {
            # Max. available data to transfer
            "max_transferred": [
                "source_node"
                "destination_node"
                "virtualized_environment",
                "structural_stability_interval",
            ],
            "max_stored": [
                "node",
                "virtualized_environment",
                "structural_stability_interval",
            ],
            "input": [
				"node",
                "virtualized_environment"
                "structural_stability_interval",
			]
        }
        data_format["transferred"] = data_format["max_transferred"]
        data_format["max_processed"] = data_format["max_stored"]
        data_format["processed"] = data_format["max_stored"]
        data_format["stored"] = data_format["max_stored"]
        data_format["dropped"] = data_format["max_stored"]


class ProcessedDataAmountMaximization:
    """
    Case:

    A network that uses virtualization technology.

    Ontology:

	- Types of operations:
		- Transfer
		- Load / save into memory
		- Process
		- Drop (due to channel constraints)
	- Network characteristics:
		- Maximum throughput
			- for transfer
			- for processing

    Objective:

    - Minimize the amount of dropped data
    - Maximize the amount of processed data

    Constraints:

    - Maximum transfer speed
    - Maximum processing speed
    - Maximum memory exchange speed
    """
    pass
