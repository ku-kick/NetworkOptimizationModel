import dataclasses
import twoopt.data_processing.data_provider
import twoopt.data_processing.vector_index
import twoopt.utility.logging


log = twoopt.utility.logging.Log(file=__file__)


class NoDataError(Exception):

    def __init__(self, variable, **index_map) -> None:
        self._variable = variable

    def __str__(self):
        return f"Can not retrieve {self._variable} where {self._index_map}"


class DataInterfaceBase:
    """
    Acquires data from an underlying data storage.
    """
    def data(self, variable, **index_map):
        """
        `variable` and `index_map` uniquely identify a piece of data. E.g.,
        for $$alpha_1$$ `data` call will look something like this:

        ```
        data("alpha", subject_area_dependent_named_subscription_index_value=1)
        ```

        Expected to raise "NoDataError", if no data can be acquired
        """
        raise NoDataError(f"Can not retrieve {variable} where {index_map}")

    def set_data(self, value, varaible, **index_map):
        raise NotImplemented


class WrappingDataInterface(DataInterfaceBase):

    def __init__(self, data_interface_implementor):
        self._data_interface_implementor = data_interface_implementor

    def data(self, *args, **kwargs):
        return self._data_interface_implementor.data(*args, **kwargs)

    def set_data(self, *args, **kwargs):
        return self._data_interface_implementor(*args, kwargs)


@dataclasses.dataclass
class GetattrDataInterface(DataInterfaceBase):
    """
    Tries to invoke named getter methods.

    Converts `data(VARIABLE, indices)` call into `VARIABLE(indices)`, and
    `set_data(VARIABLE, indices)` into `set_VARIABLE(indices)`.
    """

    _data_interface_implementor: DataInterfaceBase

    def data(self, variable, **index_map):
        try:
            return getattr(self._data_interface_implementor, variable)(
                **index_map)
        except AttributeError as e:  # Cannot find member
            return self._data_interface_implementor.data(variable, **index_map)
        except TypeError as e:  # Not callable, or wrong argument list
            return self._data_interface_implementor.data(variable, **index_map)

    def set_data(self, value, variable, **index_map):
        try:
            return getattr(self._data_interface_implementor,
                           "set_" + variable)(value, **index_map)
        except AttributeError as e:  # Cannot find member
            return self._data_interface_implementor.set_data(value,
                variable, **index_map)
        except TypeError as e:  # Not callable, or wrong argument list
            return self._data_interface_implementor.set_data(value,
                variable, **index_map)


@dataclasses.dataclass
class DefaultingDataInterface(DataInterfaceBase):
    """
    "No-value" exception-handling decorator.

    Returns default value for KeyError-producing variables
    """

    _data_interface_implementor: DataInterfaceBase
    """
    Decorated instance. See `ConstrainedDataInterface`, as it uses the same
    architectural approach
    """

    _common_default_value: object = 0
    """
    This value will be assigned to an instance, if
    `self._data_interface_implementor` raises an exception.
    """

    _default_value_override: dict = dataclasses.field(default_factory=dict)
    """
    Overrides `self._common_default_value`.
    """

    _nodefault_variables: set = dataclasses.field(default_factory=set)
    """
    Cancels `self._common_default_value` for specific variables
    """

    def data(self, variable, **index_map):
        try:
            return self._data_interface_implementor.data(variable, **index_map)
        except NoDataError as k:
            if variable in self._nodefault_variables:
                raise k
            elif variable in self._default_value_override.keys():
                return self._default_value_override[variable]
            else:
                return self._common_default_value

    def set_data(self, value, variable, **index_map):
        return self._data_interface_implementor.set_data(value, variable,
                                                         **index_map)


@dataclasses.dataclass
class IdentifierTranslatingDataInterface(DataInterfaceBase):
    """
    Stems aliases to one identifier.
    """

    _data_interface_implementor: DataInterfaceBase
    # `_translation_table` and `_aliases_list` are interchangeable
    _translation_table: dict = None
    """
    Contains entries of the following format:

    {
        STEM1: ALIAS1,  # string alias
        STEM2: [ALIAS21, ALIAS22, ...],  # list of aliases
        STEM3: (ALIAS31, ALIAS32, ...),  # tuple of aliases
    }

    Then, invoking it with, let's say, the following code:

    `object.data(ALIAS1, STEM2=2, ALAIS32=4)`

    Will be equivalent to:

    `object.data(STEM1, STEM2=2, STEM3=4)`
    """

    def __post_init__(self):
        self.__init_index()

    def __init_index(self):
        """
        Index table for aliases
        """
        self._index = dict()

        for k, v in self._translation_table:
            assert type(v) in [list, tuple, str]

            if type(v) in [list, tuple]:
                for vv in v:
                    self._index[vv] = k
            else:
                self._index[v] = k

    def _translate(self, identifier):
        if identifier in self._index.keys():
            return self._index[identifier]

        return identifier

    def data(self, variable, **index_map):
        variable = self._translate[variable]
        index_map = {self._translate(k): v for k, v in index_map.items()}

        return self._data_interface_implementor.data(variable, **index_map)

    def set_data(self, value, variable, **index_map):
        variable = self._translate[variable]
        index_map = {self._translate(k): v for k, v in index_map.items()}

        return self._data_interface_implementor.set_data(value,
            variable, **index_map)


@dataclasses.dataclass
class ConstrainedDataInterface(DataInterfaceBase):
    # TODO: apply translation table
    """
    Format-checking filter.

    Each model in this package requires data to operate on. This class is an
    encapsulation of a model's "expectations" regarding data structure it was
    been provided with.

    Boils down underlying data storages and interfaces to simple
    [
        [
            "composite_key_name_aka_variable",
            {
                "parameter_1_aka_index": VALUE,
                "parameter_2_aka_index": VALUE,
            }
        ],
        ...
    ]
    composite key mapping.
    This enables models interoperability
    """

    _data_interface_implementor: DataInterfaceBase \
        = dataclasses.field(default_factory=DataInterfaceBase)
    """
    Retrieves data from the underlying data storage (such as database).
    May also be another intermediate step
    """

    _data_format: dict = dataclasses.field(default_factory=dict)
    """
    Stores format description.
    Data structure:
    {
        variable_name: {index_set...},
        variable_name_2: {index_set_2},
        ...
    }
    """

    def _data_request_is_valid(self, variable_name: str, **index_map):
        """
        Performs data format validation using `self._data_format` description.
        """
        indices = set(index_map.keys())

        if variable_name in self._data_format.keys():
            return set(self._data_format[variable_name]) == indices

        return False

    def set_data(self, value, variable_name, **index_map):
        if not self._data_request_is_valid(variable_name, **index_map):
            raise ValueError("Data format does not comply DataInterface data \
                             definition")

        return self._data_interface_implementor.set_data(value, variable_name,
                                                         **index_map)

    def data(self, variable_name, **index_map):
        if not self._data_request_is_valid(variable_name, **index_map):
            raise ValueError("Data ")

        return self._data_interface_implementor.data(variable_name, **index_map)


@dataclasses.dataclass
class ConcreteDataInterface:

    _data_provider: twoopt.data_processing.data_provider.DataProviderBase
    """
    The storage
    """

    _schema: twoopt.data_processing.vector_index.Schema
    """
    Describes data format used by "_data_provider"
    """

    def data(self, variable_name, **index_map):
        plain_indices = self._schema.indices_dict_to_plain(variable_name,
            **index_map)[1:]

        return self._data_provider.data(variable_name, *plain_indices)

    def set_data(self, value, variable_name, **index_map):
        plain_indices = self._schema.indices_dict_to_plain(variable_name,
            **index_map)[1:]

        return self._data_provider.set_data(value, variable_name,
            *plain_indices)


def make_data_interface_wrap_chain(root, *data_interface_types):
    out = root

    for data_interface_type in data_interface_types:
        out = data_interface_type(out)

    return out
