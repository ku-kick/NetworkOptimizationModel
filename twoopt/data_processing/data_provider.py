class DataProviderBase:
	"""
	Represents underlying data as a list of entries. Can be thought of
	as a list of tuples

	[
		(VARIABLE_NAME, COMPLEX_IDENTIFIER_PART_1, ..., COMPLEX_IDENTIFIER_PART_N, VALUE),
		(VARIABLE_NAME, COMPLEX_IDENTIFIER_PART_1, ..., COMPLEX_IDENTIFIER_PART_N, VALUE),
		...
	]
	"""

	def data(self, *composite_tuple_identifier):
		pass

	def set_data(self, value, *composite_tuple_identifier):
		pass

	def into_iter(self):
		pass
