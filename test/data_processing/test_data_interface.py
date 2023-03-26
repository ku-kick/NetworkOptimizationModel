import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
print(sys.path)
import unittest
import twoopt
import twoopt.data_processing
import twoopt.data_processing.data_interface


class ConstrainedDataInterface(
        twoopt.data_processing.data_interface.ConstrainedDataInterface):

    def __init__(self) -> None:
        self._data_format = {
            "variable_1": [],
            "variable_2": ["index_a", "index_b"]
        }


class MockDataInterfaceProvider(
        twoopt.data_processing.data_interface.DataInterfaceBase):
    def variable_1(self):
        return "variable_1"

    def variable_2(self, index_a, index_b):
        return index_a + index_b


class TestDataInterface(unittest.TestCase):

    def test_defaulting_data_interface(self):
        mock = MockDataInterfaceProvider()
        getattr_wrapper \
            = twoopt.data_processing.data_interface.GetattrDataInterface(mock)
        defaulting_wrapper = \
            twoopt.data_processing.data_interface.DefaultingDataInterface(
            getattr_wrapper)
        constrained_wrapper = twoopt.data_processing.data_interface \
            .ConstrainedDataInterface(
                _data_format={
                    "variable_1": [],
                    "variable_2": ["index_a", "index_b"]
                },
                _data_interface_implementor=defaulting_wrapper,
            )

        self.assertEqual(defaulting_wrapper.data("variable_1"), "variable_1")
        self.assertEqual(defaulting_wrapper.data("variable_2", index_a=2,
                                                 index_b=5), 7)


if __name__ == "__main__":
    unittest.main()
