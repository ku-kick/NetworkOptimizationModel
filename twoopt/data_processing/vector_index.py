"""
Various tools for working with vectors, namely positions and indices thereof.

Some handled problems:

- Identify a position of a variable in matrix row using its name and
  indices;
- Get permutations of variable's indices, and iterate through them
"""

from dataclasses import dataclass, field
import copy
import functools
import itertools
import json


@dataclass
class RowIndex:
    """
    For indexed variables, it provides consistent position mapping into a
    matrix's vector.

    In linear equation's matrices, variables are stored according to some
    configuration. For example, for a problem w/ variables "x", "y", "z", a row
    could have the following structure:

    Xa0b0 Xa0b1 Xa1b0 Xa1b1 Ya0c0 ...

    This class is responsible for transforming human-readable indices into
    positions in the vector. Speaking in terms of positional numeral systems,
    the position can be represented as a tuple of mixed-radix numbers:

    (Xab, Yac)

    Essentially, this class transforms a mixed-radix number into decimal, while
    having subject area-specific API.
    """
    indices: dict  # Format {"index1": RANGE, "index2": RANGE, ...}.
    variables: dict  # Format {"variable1": [indices], "variable 2": indices, ...}
    from_zero: bool = True

    @staticmethod
    def make_from_schema(schema, variables, from_zero=True):
        index_set = functools.reduce(lambda s, var: s.union(set(schema.get_var_indices(var))), variables, set())
        indices_map = {i: schema.get_index_bound(i) for i in index_set}
        variables_map = {var: schema.get_var_indices(var) for var in variables}
        row_index = RowIndex(indices=indices_map, variables=variables_map, from_zero=from_zero)

        return row_index

    def _check_precedence(self, var_a, var_b):
        """
        Returns True, when var_a appears before var_b
        """
        return list(self.variables.keys()).index(var_a) < list(self.variables.keys()).index(var_b)

    def _to_mixed_radix_number(self, var, **indices):

        return list(map(lambda index: indices[index], self.variables[var]))

    def _get_radix_map_length(self, variable):
        return len(self.radix_maps[variable])

    def get_row_len(self):
        """
        Returns the length of the entire row
        """
        mult = lambda a, b: a * b
        map_radix_maps = map(lambda v: self.radix_maps[v], self.variables.keys())
        map_radix_map_to_decimal = map(lambda m: functools.reduce(mult, m, 1), map_radix_maps)
        res = sum(map_radix_map_to_decimal)

        return res

    def get_pos(self, variable, **indices):
        """
        Transform a mixed radix number representing the variable's position to decimal one
        """
        if not self.from_zero:
            indices = dict(map(lambda kv: (kv[0], kv[1] - 1), indices.items()))

        assert variable in self.variables.keys()  # Check if variable exists
        assert set(indices.keys()) == set(self.variables[variable])  # Check that all indices are present
        assert all([0 <= indices[i] <= self.indices[i] for i in indices.keys()])

        radix_number = self._to_mixed_radix_number(variable, **indices)
        mult = lambda a, b: a * b

        map_var = lambda var: sum(map(lambda i: radix_number[i] * self.radix_mult_vectors[var][i],
            range(len(self.radix_maps[var])))) if var == variable else 0 if self._check_precedence(var, variable) else \
            functools.reduce(mult, self.radix_maps[var], 1)

        return sum(map(map_var, self.variables.keys()))

    __call__ = get_pos

    def __post_init__(self):
        """
        Forms radix map and radix scalar multiplication vector for numerical transofmations into a non-mixed radix
        number

        Example:
        indices: {j: 2, rho: 3}
        variables {x: [j, rho], y: [j]}
        radix map for x: [2, 3]

        With this radix map, a mixed radix number [1, 2, 1] could be converted into a non-mixed through multiplication:

        [1, 2, 1] * radix_mult_vector
        """
        self.radix_maps = dict(zip(self.variables.keys(), map(lambda variable: list(map(
            lambda index: self.indices[index], self.variables[variable])), self.variables.keys())))
        self.radix_mult_vectors = dict()

        for v in self.variables.keys():
            npos = len(self.radix_maps[v])
            self.radix_mult_vectors[v] = [1 for _ in range(npos)]

            if npos > 1:
                for i in reversed(range(npos - 1)):
                    self.radix_mult_vectors[v][i] = self.radix_maps[v][i + 1] * self.radix_mult_vectors[v][i + 1]


def radix_cartesian_product(radix_boundaries):
    if len(list(radix_boundaries)) == 0:
        return [[]]

    mapped = map(range, radix_boundaries)
    return itertools.product(*mapped)


@dataclass
class Schema:
    """
    Wrapper over a dictionary containing schema information: indices, variables, boundaries
    Format example:
    {
        "indexbound": {
            "j": 3,
            "i": 2,
            "m": 4
        },
        "variableindices": {
            "x": ["j", "i"],
            "y": ["i", "j", "m"],
            "z": ["i", "m"]
        }
    }

    Bounds are counted from 0 to N: [0; N)
    """
    data: dict = field(default_factory=dict)
    filename: str = None

    def set_index_bounds(self, **index_to_bounds):
        if "indexbound" not in self.data.keys():
            self.data["indexbound"] = dict()

        for k, v in index_to_bounds.items():
            self.data["indexbound"][k] = v

    def set_variable_indices(self, **variable_to_ordered_index_list):
        if "variableindices" not in self.data.keys():
            self.data["variableindices"] = dict()

        for k, v in variable_to_ordered_index_list.items():
            self.data["variableindices"][k] = list(v)

    def __post_init__(self):
        if self.filename is not None:
            self.read(self.filename)

    def read(self, filename="schema.json"):
        with open(filename, 'r') as f:
            try:
                self.data = json.loads(f.read())
            except FileNotFoundError as e:
                Log.error(Schema, "got exception", e)
                self.data = {
                    "indexbound": dict(),
                    "variableindices": dict(),
                }

    def variables(self):
        return copy.deepcopy(list(self.data["variableindices"].keys()))

    def write(self, filename="schema.json"):
        assert self.data is not None
        with open(filename, 'w') as f:
            f.write(self.data)

    def set_index_bound(self, index, bound):
        assert self.data is not None
        self.data["indexbound"][index] = bound

    def get_index_bound(self, index):
        assert self.data is not None
        assert index in self.data["indexbound"]
        return self.data["indexbound"][index]

    def make_radix_map(self, *indices):
        """
        Makes an array of upper bounds using the indices provided
        """
        return list(self.get_index_bound(i) for i in indices)

    def set_var_indices(self, var, *indices):
        assert self.data is not None
        assert len(indices) > 0
        self.data["variableindices"][var] = list(indices)

    def get_var_indices(self, var):
        assert self.data is not None
        assert var in self.data["variableindices"]
        return self.data["variableindices"][var]

    def get_var_radix(self, var):
        """
        A tuple of variable indices can be represented as a mixed-radix number. Returns base of that number
        """
        assert var in self.data["variableindices"]

        return list(map(lambda i: self.data["indexbound"][i], self.data["variableindices"][var]))

    get_radix_map = get_var_radix

    def radix_map_iter(self, *indices):
        radix_map = self.make_radix_map(*indices)

        for ind in radix_cartesian_product(radix_map):
            yield ind

    def radix_map_iter_dict(self, *indices):
        for ind in self.radix_map_iter(*indices):
            yield {k: v for k, v in zip(indices, ind)}

    def radix_map_iter_var(self, var):
        indices = self.get_var_indices(var)
        yield from self.radix_map_iter(*indices)

    def radix_map_iter_var_dict(self, var):
        for ind in self.radix_map_iter_var(var):
            yield self.indices_plain_to_dict(var, *ind)

    def indices_dict_to_plain(self, variable, **indices):
        """
        [VARAIBLE, {"index1": INDEX1, "index2": INDEX2}] -> [VARIABLE, INDEX1, INDEX2]
        """
        assert type(variable) is str
        assert set(self.data["variableindices"][variable]) == set(indices.keys())
        indices_plain = tuple(map(lambda i: indices[i], self.data["variableindices"][variable]))

        return (variable,) + indices_plain

    def indices_plain_to_dict(self, variable, *indices):
        """
        [VARIABLE, INDEX1, INDEX2] -> [VARAIBLE, {"index1": INDEX1, "index2": INDEX2}]
        """
        assert type(variable) is str
        check_type_int = lambda i: type(i) is int
        assert all(map(check_type_int, indices))
        assert len(indices) == len(self.data["variableindices"][variable])
        indices_dict = dict(zip(self.data["variableindices"][variable], indices))

        return (variable, indices_dict)
