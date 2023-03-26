import dataclasses


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
        Expected to raise "NoDataError", if no data can be acquired
        """
        raise NoDataError(f"Can not retrieve {variable} where {index_map}")

    def set_data(self, value, varaible, **index_map):
        raise NotImplemented


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

    _common_default_value: object = 0.0
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
class ConstrainedDataInterface(DataInterfaceBase):
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

    _data_interface_implementor: DataInterfaceBase \
        = dataclasses.field(default_factory=DataInterfaceBase)
    """
    Retrieves data from the underlying data storage (such as database).
    May also be another intermediate step
    """

    def _data_request_is_valid(self, variable_name: str, **index_map):
        """
        Performs data format validation using `self._data_format` description.
        """
        indices = set(index_map.keys())

        if variable_name in self._data_format.keys():
            return set(self._data_format[variable_name]) == indices

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
