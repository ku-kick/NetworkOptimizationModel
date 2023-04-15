
class DataProcessor:
    """
    Operates on input data, produces an output
    """
    def __init__(self, data_interface)
        """
        `data_interface` is expected to come pre-initialized
        """
        self._data_interface = data_interface

    def run(self):
        raise NotImplemented

    def get_data_interface(self):
        return self._data_interface


class Solver(DataProcessor):

    def __init__(self, data_interface, schema):
        # TODO: does a solver really need a schema instance? Remove it
        DataProcessor.__init__(self, data_interface)
        self._schema = schema

    def get_schema(self):
        return self._schema


class Simulation(DataProcessor):

    def __init__(self, data_interface):
        DataProcessor.__init__(self, data_interface=data_interface)

    def run(self):
        raise NotImplemented
