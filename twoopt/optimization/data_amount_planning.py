import dataclasses
import math
import numpy as np
import scipy
import twoopt.data_processing.data_interface
import twoopt.data_processing.data_processor
import twoopt.data_processing.data_provider
import twoopt.data_processing.vector_index



SCHEMA_VARIABLEINDICES = {
    "x": ["j", "i", "rho", "l"],
    "y": ["j", "rho", "l"],
    "g": ["j", "rho", "l"],
    "z": ["j", "rho", "l"],
    "psi": ["j", "i", "rho", "l"],
    "phi": ["j", "rho", "l"],
    "v": ["j", "rho", "l"],
    "x_eq": ["j", "rho", "l"],
    "mm_psi": ["j", "i", "l"],
    "m_psi": ["j", "i", "rho", "l"],
    "mm_v": ["j", "l"],
    "m_v": ["j", "rho", "l"],
    "mm_phi": ["j", "l"],
    "m_phi": ["j", "rho", "l"],
    "x^": ["j", "i", "rho", "l"],
    "y^": ["j", "rho", "l"],
    "g^": ["j", "rho", "l"],
    "z^": ["j", "rho", "l"],
    "x_eq^": ["j", "rho", "l"],
    "alpha_0": [],
    "alpha_1": [],
    "dt": [],
    "tl": ["l"],
    "nodes": [],
    "structural_stability_intervals": [],
    "virtualized_environments": [],
}


def make_schema(max_nodes, max_virtualized_environments,
        max_structural_stability_intervals):
    schema = twoopt.data_processing.vector_index.Schema(dict(
        indexbound={
            "j": max_nodes,
            "i": max_nodes,
            "rho": max_virtualized_environments,
            "l": max_structural_stability_intervals,
        },
        variableindices=SCHEMA_VARIABLEINDICES,
    ))

    return schema


class StubLog:

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


log = StubLog()


class _DataInterfaceLegacyAdapter(twoopt.data_processing.data_interface.ConcreteDataInterface):
    """
    Previous implementation had sh*tload of boilerplate ETL, w/ various
    getters and setters
    """

    def __init__(
            self,
            data_interface_implementor:
                twoopt.data_processing.data_interface.DataInterfaceBase,
            schema: twoopt.data_processing.vector_index.Schema):
        self._data_interface = data_interface_implementor
        self._schema = schema

    def get(self, variable, **indices):
        return self._data_interface.data(variable, **indices)

    def set(self, variable, value, **indices):
        return self._data_interface.set_data(value, variable, **indices)

    def get_plain(self, variable, *indices):
        index_map = self._schema.indices_plain_to_dict(variable, *indices)
        index_map = index_map[1]  # index_map has `(VARIABLE, {INDICES: INDICES})` structure

        return self._data_interface.data(variable, **index_map)


@dataclasses.dataclass
class LinsolvPlanner(twoopt.data_processing.data_processor.Solver):
    """
    Domain-aware linear equation solver.

    It is difficult to gain a comprehensive understanding of this code w/o the
    context. If you speak russian, please refer to the 2022 paper "Polymodel
    optimization of network configuration and informational operations schedule,
    problem statement and solving approaches"
    """
    data_interface: object
    schema: object

    # Mapping b/w a network config. characteristic, and the name of the variable
    # representing its upper bound (lower bounds are always 0)
    _NEQ_VAR_ORDER = ['x', 'y', 'g', 'z']
    _NEQ_VAR_ORDER_RHS = ["psi", "v", "phi"]

    def __post_init__(self):
        twoopt.data_processing.data_processor.Solver.__init__(self, self.data_interface, self.schema)
        self.row_index = twoopt.data_processing.vector_index.RowIndex \
            .make_from_schema(self.schema, ["y", "x", "z", "g"])
        self.validate()
        self.eq_lhs, self.eq_rhs = self.__make_eq()
        self.bnd = self.__init_bnd_matrix()
        self.obj = self.__init_obj()

    def __make_eq_lhs_rhs(self, j, rho, l):
        assert self.schema.get_index_bound("j") == self.schema.get_index_bound("i")
        vec = np.zeros(self.row_index.get_row_len())
        g_pos = self.row_index.get_pos("g", j=j, rho=rho, l=l)
        y_pos = self.row_index.get_pos("y", j=j, rho=rho, l=l)
        z_pos = self.row_index.get_pos("z", j=j, rho=rho, l=l)
        vec[g_pos] = 1
        vec[y_pos] = 1
        vec[z_pos] = 1

        if l > 0:
            y_prev_pos = self.row_index.get_pos("y", j=j, rho=rho, l=l - 1)
            vec[y_prev_pos] = -1

        for i in range(self.schema.get_index_bound("j")):
            if i != j:
                # Input: negative coefficient
                x_in_pos = self.row_index.get_pos("x", j=i, i=j, rho=rho, l=l)
                vec[x_in_pos] = -1
                # Output: positive coefficient
                x_out_pos = self.row_index.get_pos("x", j=j, i=i, rho=rho, l=l)
                vec[x_out_pos] = 1

        rhs = self.data_interface.get("x_eq", j=j, rho=rho, l=l)

        return vec, rhs

    def __make_eq(self):
        lhs = []
        rhs = []

        for indices in self.schema.radix_map_iter_var_dict("x_eq"):
            j = indices[1].pop("j")
            rho = indices[1].pop("rho")
            l = indices[1].pop("l")
            assert len(indices[1].items()) == 0  # There should only be "j", "rho", and "l"
            lhs_next, rhs_next = self.__make_eq_lhs_rhs(j=j, rho=rho, l=l)
            lhs.append(lhs_next)
            rhs.append(rhs_next)

        return lhs, rhs

    def validate(self):
        """
        Ensures input data correctness
        """
        assert self.schema.get_index_bound("i") == self.schema.get_index_bound("j")
        assert list(self.schema.get_var_indices("x")) == ["j", "i", "rho", "l"]

        for var in ["x_eq", "y", "g", "z"]:
            log.debug(LinsolvPlanner, LinsolvPlanner.validate, "var", var, self.schema.get_var_indices(var))
            assert list(self.schema.get_var_indices(var)) == ["j", "rho", "l"]

    def __init_bnd_matrix(self):
        bnd = [[0, float("inf")] for _ in range(self.row_index.get_row_len())]

        for var, bnd_var in zip(LinsolvPlanner._NEQ_VAR_ORDER, LinsolvPlanner._NEQ_VAR_ORDER_RHS):
            # "z" upper limit is always "inf". It is not expected in input data
            if var != "z":
                assert list(self.schema.get_var_indices(var)) == list(self.schema.get_var_indices(bnd_var))

            for indices in twoopt.data_processing.vector_index.radix_cartesian_product(self.schema.get_var_radix(var)):
                _, indices_dict = self.schema.indices_plain_to_dict(var, *indices)  # ETL
                pos = self.row_index.get_pos(var, **indices_dict)
                upper_bound = self.data_interface.get_plain(bnd_var, *indices)
                log.debug("var", var, "indices", indices, "upper_bound", upper_bound, "pos", pos)
                bnd[pos][1] = upper_bound

        log.debug("bnd", '\n\t' + '\n\t'.join(list(map(str, enumerate(bnd)))))
        return bnd

    def __init_obj(self):
        alpha_g = -self.data_interface.get_plain(
            "alpha_0")  # alpha_1 in the paper, inverted, because numpy can only solve minimization problems
        alpha_z = self.data_interface.get_plain(
            "alpha_1")  # alpha_2 in the paper, inverted, because numpy can only solve minimization problems
        assert not math.isclose(alpha_g, 0.0, abs_tol=1e-6)
        assert not math.isclose(alpha_z, 0.0, abs_tol=1e-6)
        stub = np.zeros(self.row_index.get_row_len())

        for j, rho, l in twoopt.data_processing.vector_index.radix_cartesian_product(self.schema.make_radix_map("j", "rho", "l")):
            pos_g = self.row_index.get_pos("g", j=j, rho=rho, l=l)
            pos_z = self.row_index.get_pos("z", j=j, rho=rho, l=l)
            stub[pos_g] = alpha_g
            stub[pos_z] = alpha_z

        return stub

    def run(self):
        return self.solve()

    def solve(self):
        solution = scipy.optimize.linprog(c=self.obj, bounds=self.bnd, A_eq=self.eq_lhs, b_eq=self.eq_rhs)
        assert 0 == solution.status

        if 0 == solution.status:
            # Log.info(LinsolvPlanner.solve, "registering solution results in data interface")
            for variable in self.row_index.variables.keys():
                for indices in self.schema.radix_map_iter_var_dict(variable):
                    log.debug(LinsolvPlanner.solve, indices)
                    pos = self.row_index.get_pos(variable, **indices[1])
                    self.data_interface.set(variable, solution.x[pos], **indices[1])

        return solution


class _Schema(twoopt.data_processing.vector_index.Schema):

    def __init__(self):
        twoopt.data_processing.vector_index.Schema.__init__(self)
        self.set_index_bounds(j=0, i=0, rho=0, l=0)
        self.set_variable_indices(**SCHEMA_VARIABLEINDICES)

    def init_index_bounds(
            self,
            data_interface: twoopt.data_processing.data_interface \
                .DataInterfaceBase):
        for human_readable_identifier, internal_identifier in zip(
                [
                    "nodes",
                    "nodes",
                    "virtualized_environments",
                    "structural_stability_intervals"
                ],
                ["j", "i", "rho", "l"]):
            bound = data_interface.data(human_readable_identifier)
            self.set_index_bound(internal_identifier, bound)


class _InferencingDataInferface(
        twoopt.data_processing.data_interface.WrappingDataInterface):
    """
    During simulation, constraints are decomposed:

    psi = mm_psi * m_psi
    phi = mm_phi * m_phi
    v = mm_v * m_v
    """

    def data(self, variable, **index_map):
        try:
            return self._data_interface_implementor.data(variable, **index_map)
        except (twoopt.data_processing.data_interface.NoDataError, ValueError):
            if variable == "phi":
                return self._data_interface_implementor.data("mm_phi", **index_map) \
                    * self._data_interface_implementor.data("m_phi", **index_map)
            elif variable == "psi":
                return self._data_interface_implementor.data("mm_psi", **index_map) \
                    * self._data_interface_implementor.data("m_psi", **index_map)
            elif variable == "v":
                return self._data_interface_implementor.data("mm_v", **index_map) \
                    * self._data_interface_implementor.data("m_v", **index_map)
            else:
                return self._data_interface_implementor.data(variable, **index_map)


class _IdentifierTranslatingDataInterface(
        twoopt.data_processing \
            .data_interface.IdentifierTranslatingDataInterface):

    TRANSLATION_TABLE = {
        "max_transferred": "mm_psi",
        "max_stored": "mm_v",
        "max_processed": "mm_phi",
        "transferred_fraction": "m_psi",
        "stored_fraction": "m_v",
        "processed_fraction": "m_phi",
        "max_transferred_per_virtualized_environment": "psi",
        "max_stored_per_virtualized_environment": "v",
        "max_processed_per_virtualized_environment": "phi",
        "source_node": "j",
        "destination_node": "i",
        "node": "j",
        "virtualized_environment": "rho",
        "structural_stability_interval": "l",
        "processed": "g",
        "dropped": "z",
        "stored": "y",
        "transferred": "x",
        "nodes": "J",
        "virtualized_environments": "Rho",
        "structural_stability_intervals": "L",
        "minimize_drop_importance": "alpha_1",
        "maximize_processing_importance": "alpha_0",
    }

    def __init__(self, data_interface_implementor:
                twoopt.data_processing.data_interface.DataInterfaceBase):
            twoopt.data_processing.data_interface \
                .IdentifierTranslatingDataInterface.__init__(
                self,
                data_interface_implementor,
                _IdentifierTranslatingDataInterface.TRANSLATION_TABLE)


class _DefaultingDataInterface(
        twoopt.data_processing.data_interface.DefaultingDataInterface):
    def __init__(self, data_interface_implementor):
        twoopt.data_processing.data_interface.DefaultingDataInterface.__init__(
            self,
            _data_interface_implementor=data_interface_implementor)


def _make_data_interface_schema_helper(data_provider):
    """
    Schema depends on data interface, because it needs to initialize its index
    bounds. Data interface depends on schema to acquire raw data. Plus, data
    interface will have multiple filters such as "translating data interface",
    "defaulting" one, etc.
    """
    schema = _Schema()
    concrete_data_interface = twoopt.data_processing.data_interface\
        .ConcreteDataInterface(data_provider, schema)
    output_data_interface = twoopt.data_processing.data_interface\
        .make_data_interface_wrap_chain(
            concrete_data_interface,
            _InferencingDataInferface,
            _DefaultingDataInterface
        )
    schema.init_index_bounds(output_data_interface)

    return output_data_interface, schema


class _ConstrainedDataInterface(
        twoopt.data_processing.data_interface.ConstrainedDataInterface):
    def __init__(self, data_interface: \
                 twoopt.data_processing.data_interface.DataInterfaceBase):
        data_format = {
            # Max. available data to transfer
            "max_transferred_per_virtualized_environment": [
                "source_node"
                "destination_node"
                "virtualized_environment",
                "structural_stability_interval",
            ],
            "max_stored_per_virtualized_environment": [
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
        data_format["max_processed"] = [
            "node",
            "structural_stability_interval"
        ]
        data_format["max_stored"] = ["node", "structural_stability_interval"]
        data_format["max_stored"] = [
            "source_node",
            "destination_node",
            "structural_stability_interval"
        ]
        data_format["transferred"] \
            = data_format["max_transferred"]  # Amount of data transferred
        data_format["max_processed_per_virtualized_environment"] \
            = data_format["max_stored"]
        data_format["processed"] = data_format["max_stored"]
        data_format["stored"] = data_format["max_stored"]
        data_format["dropped"] = data_format["max_stored"]
        data_format["minimize_drop_importance"] = []  # alpha_1, alpha_z, or alpha_2, depending on whether it is counted from 0
        data_format["maximize_processing_importance"] = []  # alpha_0, alpha_g, or alpha_1, depending on whether it is counted from 0
        data_format["nodes"] = []  # Number of nodes
        data_format["virtualized_environments"] = []  # Number of virtualized environments
        data_format["structural_stability_intervals"] = []  # Number of virtualized environments
        twoopt.data_processing.data_interface.ConstrainedDataInterface(
            data_interface, data_format)


class ProcessedDataAmountMaximizationSolver(
        twoopt.data_processing.data_processor.Solver):
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
    def __init__(self, data_provider: twoopt.data_processing.data_provider \
            .DataProviderBase):
        self._data_interface, self._schema \
            = _make_data_interface_schema_helper(data_provider)
        twoopt.data_processing.data_processor.Solver.__init__(
            self,
            data_interface=self._data_interface,
            schema=self._schema
        )
        self._legacy_data_interface = _DataInterfaceLegacyAdapter(
            self._data_interface, self._schema)
        self._legacy_solver = LinsolvPlanner(
            self._legacy_data_interface,
            self._schema)
