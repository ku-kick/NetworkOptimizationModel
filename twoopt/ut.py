import itertools
import datetime
from dateutil import parser as date_parser
import os


def iter_plain(root):
	try:
		for i in root:
			yield from iter_plain(i)
	except TypeError:
		yield root


def radix_cartesian_product(radix_boundaries):
	if len(list(radix_boundaries)) == 0:
		return [[]]

	mapped = map(range, radix_boundaries)
	return itertools.product(*mapped)


def file_create_if_not_exists(filename):
	if not os.path.exists(filename):
		with open(filename, 'w'):
			pass


def clamp(val, vmin=-float("inf"), vmax=float("inf")):
	return max(min(val, vmax), vmin)


class Datetime:
	DATE_FORMAT = "%Y-%m-%d"
	TIME_FORMAT = "%Y%m%d%H%M"

	@staticmethod
	def today():
		return datetime.datetime.now()

	@staticmethod
	def yesterday():
		return datetime.datetime.now() - datetime.timedelta(days=1)

	@staticmethod
	def format(d):
		return datetime.datetime.strftime(d, Datetime.DATE_FORMAT)

	@staticmethod
	def format_time(d):
		return datetime.datetime.strftime(d, Datetime.TIME_FORMAT)

	@staticmethod
	def parse(d: str):
		return date_parser.parse(d)
