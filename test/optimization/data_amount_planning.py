import twoopt.data_processing.data_provider
import twoopt.data_processing.vector_index
import twoopt.optimization.data_amount_planning
import unittest


_SIMPLE_AB_TRANSFER_DATA = (
    ("psi",                            0,   1, 0,   0,   10,  ),
    ("phi",                            1,   0, 0,   10,  ),
    ("x_eq",                           0,   0, 0,   10,  ),
    ("mm_psi",                         0,   1, 0,   0,   1.0, ),
    ("m_psi",                          0,   1, 0,   0,   0.0, ),
    ("mm_phi",                         0,   1, 1.0, ),
    ("m_phi",                          0,   1, 0,   0.0, ),
    ("tl",                             0,   5, ),
    ("tl",                             1,   5, ),
    ("alpha_1",                        0.5, ),
    ("alpha_0",                        0.5, ),
    ("nodes",                          2),
    ("virtualized_environments",       2,),
    ("structural_stability_intervals", 2,),
)


class Test(unittest.TestCase):

    def test_simple_transfer(self):
        data_provider = twoopt.data_processing.data_provider.RamDataProvider()
        data_provider.set_data_from_rows(_SIMPLE_AB_TRANSFER_DATA)
        solver = twoopt.optimization.data_amount_planning\
            .ProcessedDataAmountMaximizationSolver(data_provider=data_provider)
        solver.run()


if __name__ == "__main__":
    unittest.main()
