class DataProviderBase:
	"""
	Represents underlying data as a list of entries. Can be thought of
	as a list of tuples

	[
		(COMPLEX_IDENTIFIER_PART_1, ..., COMPLEX_IDENTIFIER_PART_N, VALUE),
		(COMPLEX_IDENTIFIER_PART_1, ..., COMPLEX_IDENTIFIER_PART_N, VALUE),
		...
	]
	"""

	def data(self, *composite_tuple_identifier):
		pass

	def set_data(self, value, *composite_tuple_identifier):
		pass
