"""

Legacy ETL is a bunch of poorly aligned ad-hoc data-processing utilities. So
there is a need for an additional layer on top of the old data
representation-related entities.

"""

import twoopt.optimization.data_amount_planning


def data_amount_planning_make_legacy_env(data_provider):
    from twoopt.simulation.network_data_flow import _LegacyEnv
    from twoopt.optimization.data_amount_planning import \
        make_data_interface_schema_helper

    data_interface, schema = make_data_interface_schema_helper(data_provider)
    legacy_env = _LegacyEnv(data_interface, schema, data_provider)

    return legacy_env


def data_amount_planning_make_legacy_virt_helper(data_provider):
    from twoopt.linsmat import VirtHelper

    legacy_env = data_amount_planning_make_legacy_env(data_provider)
    legacy_virt_helper = VirtHelper(legacy_env)

    return legacy_virt_helper


def data_amount_planning_make_simulation_constructor(data_provider):
    """
    Legacy simulation constructor is expected to return simulation instance
    from data interface and schema. With the new simulation implementation (
    which is a wrapper over the old one) there is no need for such a
    fine-grained construction process.
    """
    def simulation_constructor(*args, **kwrags):
        from twoopt.simulation.network_data_flow import NetworkDataFlow

        # The new implementation is derived from the legacy one, so those are fully compatible
        return NetworkDataFlow(data_provider=data_provider)

    return simulation_constructor


def data_interface_initialize_from_legacy_data_interface(data_interface,
        legacy_data_interface):
    # TODO
    pass


def make_data_interface_from_legacy_data_interface(legacy_data_interface):
    # TODO
    pass
