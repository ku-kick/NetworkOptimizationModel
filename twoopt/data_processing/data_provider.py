import csv
import dataclasses
import io
import os


class DataProviderBase:
    """
    Represents underlying data as a list of entries. Can be thought of
    as a list of tuples

    [
        (VARIABLE_NAME, COMPLEX_IDENTIFIER_PART_1, ..., COMPLEX_IDENTIFIER_PART_N, VALUE),
        (VARIABLE_NAME, COMPLEX_IDENTIFIER_PART_1, ..., COMPLEX_IDENTIFIER_PART_N, VALUE),
        ...
    ]

    If the implementor cannot satisfy the request due to lack of data, it
    must raise `twoopt.data_processing.data_interface.NoDataError(...)`
    """

    def data(self, *composite_tuple_identifier):
        pass

    def set_data(self, value, *composite_tuple_identifier):
        pass

    def into_iter(self):
        pass

    def set_data_from_rows(self, iterable_rows):
        """
        Rows must have the following format: `(VARIABLE, ID1, ID2, ..., VALUE)`
        """
        for row in iterable_rows:
            assert len(row) >= 2
            value = row[-1]
            composite_key = row[0:-1]
            self.set_data(value, *composite_key)


class RamDataProvider(dict, DataProviderBase):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        DataProviderBase.__init__(self)

    def data(self, *composite_tuple_identifier):
        import twoopt.data_processing.data_interface

        if composite_tuple_identifier not in self:
            raise twoopt.data_processing.data_interface.NoDataError(composite_tuple_identifier)

        try:
            return self[composite_tuple_identifier]
        except KeyError:
            raise twoopt.data_processing.data_interface.NoDataError(str(composite_tuple_identifier))

    def set_data(self, value, *composite_tuple_identifier):
        self[composite_tuple_identifier] = value

    def into_iter(self):
        for k, v in self.items():
            yield *k, v


@dataclasses.dataclass
class PermissiveCsvBufferedDataProvider(dict, DataProviderBase):
    """
    CSV with mixed whitespace / tab delimiters.

    Guarantees and ensures that VARIABLE has type `str`, indices have type
    `int`, and VALUE has type `float`
    """
    csv_file_name: str

    def data(self, *composite_tuple_identifier):
        import twoopt.data_processing.data_interface

        try:
            return self.get_plain(*composite_tuple_identifier)
        except:
            raise twoopt.data_processing.data_interface.NoDataError(composite_tuple_identifier)

    def set_data(self, value, *composite_tuple_identifier):
        self.set_plain(*composite_tuple_identifier, value)

    def get_plain(self, *key):
        assert key in self.keys()
        return self[key]

    def set_plain(self, *args):
        """
        Adds a sequence of format (VAR, INDEX1, INDEX2, ..., VALUE) into the dictionary
        """
        assert len(args) >= 2
        line_to_kv: object = lambda l: (tuple([l[0]] + list(map(int, l[1:-1]))), float(l[-1]))
        k, v = line_to_kv(args)
        self[k] = v

    def into_iter(self):
        stitch = lambda kv: kv[0] + (kv[1],)

        return map(stitch, self.items())

    def __post_init__(self):
        """
        Parses data from a CSV file containing sequences of the following format:
        VARIABLE   SPACE_OR_TAB   INDEX1   SPACE_OR_TAB   INDEX2   ...   SPACE_OR_TAB   VALUE

        Expects the values to be stored according to Repr. w/ use of " " space symbol as the separator
        """
        assert os.path.exists(self.csv_file_name)

        try:
            with open(self.csv_file_name, 'r') as f:
                lines = f.readlines()
                data = ''.join(map(lambda l: re.sub(r'( |\t)+', ' ', l), lines))  # Sanitize, replace spaces or tabs w/ single spaces
                data = data.strip()
                reader = csv.reader(io.StringIO(data), delimiter=' ')

                for plain in reader:
                    self.set_plain(*plain)

        except FileNotFoundError:
            pass

    def sync(self):
        with open(self.csv_file_name, 'w') as f:
            writer = csv.writer(f, delimiter=' ')

            for l in self.into_iter():
                writer.writerow(l)
