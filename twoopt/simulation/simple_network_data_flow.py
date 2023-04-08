import twoopt.data_processing.data_interface
import twoopt.data_processing.data_processor
import twoopt.data_processing.vector_index
import twoopt.legacy_simulation
import twoopt.linsmat
import twoopt.optimization.data_amount_planning

from twoopt.optimization.data_amount_planning import _DataInterfaceLegacyAdapter


class _LegacyEnv(twoopt.linsmat.Env):
    def __init__(
            self,
            data_interface_implementor: \
                twoopt.data_processing.data_interface.DataInterfaceBase,
            schema: twoopt.data_processing.vector_index.Schema):
        row_index = twoopt.data_processing.vector_index.RowIndex\
            .make_from_schema(schema=schema, variables=list())
        data_interface_legacy_adapter = _DataInterfaceLegacyAdapter(
            data_interface_implementor=data_interface_implementor,
            schema=schema)
        twoopt.linsmat.Env.__init__(self, row_index=row_index, schema=schema,
            data_interface=data_interface_legacy_adapter)


class NetworkDataFlow(
        twoopt.legacy_simulation.Simulation,
        twoopt.data_processing.data_processor.Simulation):

    def __init__(self, data_interface_implementor, schema):
        legacy_env = _LegacyEnv(
            data_interface_implementor=data_interface_implementor,
            schema=schema)
        twoopt.data_processing.data_processor.Simulation.__init__(self,
            data_interface=data_interface_implementor)
        twoopt.legacy_simulation.Simulation.__init__(env=legacy_env)
