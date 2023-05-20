"""

`DataInterface` instances perform high-level data operations, such as data
validation, boundary checks, etc.

"""

import dataclasses
import twoopt.data_processing.data_provider
import twoopt.data_processing.vector_index
import twoopt.utility.logging


log = twoopt.utility.logging.Log(file=__file__)


class NoDataError(Exception):

    def __init__(self, variable=None, **index_map) -> None:
        message = index_map.pop("message", None)
        if message:
            Exception.__init__(self, message)
        else:
            Exception.__init__(self, f"Can not retrieve {variable}{index_map}.")


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

    def set_data(self, value, variable, **index_map):
        raise NotImplemented


class WrappingDataInterface(DataInterfaceBase):

    def __init__(self, data_interface_implementor):
        DataInterfaceBase.__init__(self)
        self._data_interface_implementor = data_interface_implementor

    def data(self, *args, **kwargs):
        return self._data_interface_implementor.data(*args, **kwargs)

    def set_data(self, *args, **kwargs):
        return self._data_interface_implementor.set_data(*args, **kwargs)


class GetattrDataInterface(WrappingDataInterface):
    """
    Tries to invoke named getter methods.

    Converts `data(VARIABLE, indices)` call into `VARIABLE(indices)`, and
    `set_data(VARIABLE, indices)` into `set_VARIABLE(indices)`.
    """

    def __init__(self, data_interface_implementor):
        self.__dict__["_data_interface_implementor"] = data_interface_implementor

    def __getattr__(self, item):
        return self.data(item)

    def __setattr__(self, key, value):
        return self.set_data(value=value,
            variable=key)


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

    _prohibited_default_variables: set = dataclasses.field(default_factory=set)
    """
    Cancels `self._common_default_value` for specific variables. If not empty,
    all variables will be considered defaultable except those specified in this
    set. Cannot be used if `_allowed_default_variables` is not empty.
    """

    _allowed_default_variables: set = dataclasses.field(default_factory=set)
    """
    If not empty, only this set of variables will be considered overridable.
    Cannot be used while `_prohibited_default_variables` is not empty.
    """

    def __post_init__(self):
        # Sanity check: either all variables are subject to override by
        # default, or none of those are, with the expeptions specified in the
        # respective lists (sets)
        if len(self._allowed_default_variables) != 0 \
                and len(self._prohibited_default_variables) != 0:
            raise Exception("Conflicting filters. Either `_allowed_default_variables` or `_prohibited_default_variables` may have none-zero length")

    def data(self, variable, **index_map):
        try:
            return self._data_interface_implementor.data(variable, **index_map)
        except NoDataError as k:
            # Check whether the variable is allowed to be overridden
            if len(self._allowed_default_variables) != 0 and variable \
                    not in self._allowed_default_variables:
                raise NoDataError(message=f"DefaultingDataInterface: missing variable `{variable}` cannot be defaulted, as it is not in the list of overridable variables")
            elif len(self._prohibited_default_variables) != 0\
                    and variable in self._prohibited_default_variables:
                raise NoDataError(message=f"DefaultingDataInterface: missing variable `{variable}` cannot be defaulted, as it is in the list of non-overridable variables")

            # Infer the variable's override value
            if variable in self._default_value_override.keys():
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
class ConstrainedDataInterface(WrappingDataInterface):
    # TODO: apply translation table
    """
    Format-checking filter.

    Applies schema to verify the format of variable which value is attempted to
    be inferred.
    """

    def __init__(self, data_interface_implementor, schema):
        WrappingDataInterface.__init__(self, data_interface_implementor)
        self._schema = schema
        self._format_error_message = ""

    def _data_request_is_valid(self, variable_name: str, **index_map):
        if variable_name not in self._schema.variables():
            self._format_error_message = f"Variable `{variable_name}` has not been expected"
            return False

        return True

    def set_data(self, value, variable_name, **index_map):
        if not self._data_request_is_valid(variable_name, **index_map):
            log.warning(ConstrainedDataInterface.set_data,
                self._format_error_message)

        return self._data_interface_implementor.set_data(value, variable_name,
                                                         **index_map)

    def data(self, variable_name, **index_map):
        if not self._data_request_is_valid(variable_name, **index_map):
            log.warning(ConstrainedDataInterface.set_data,
                self._format_error_message)

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

    def data_provider(self):
        return self._data_provider

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
