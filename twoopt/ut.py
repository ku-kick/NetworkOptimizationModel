import itertools
import datetime
from dateutil import parser as date_parser
import os
from dataclasses import dataclass, field
from generic import Log
import pathlib
import os
import inspect


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


def file_here_to_str_path(here, *args):
	file = pathlib.Path(here).parent

	for a in args:
		file = file / a

	return file.resolve()


def clamp(val, vmin=-float("inf"), vmax=float("inf")):
	return max(min(val, vmax), vmin)


def frange(base, ceil, step):
	assert step != 0
	assert base != ceil
	assert (base < ceil) == (step > 0)

	if base < ceil:
		cmp = lambda a, b: a < b
	else:
		cmp = lambda a, b: a > b

	while cmp(base, ceil):
		yield base

		base += step


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


@dataclass
class Trace:
	"""
	Accumulated history of ticks
	"""

	state: dict = field(default_factory=dict)

	@dataclass
	class TimePoint:
		title: str
		vert_bound: list
		t: float

		def as_line_x1y1(self):
			return [(self.t, self.vert_bound[0]), (self.t, self.vert_bound[1])]

	@dataclass
	class ValueThreshold:
		title: str
		hor_bound: list
		val: float

		def as_line_x1y1(self):
			return [(self.hor_bound[0], self.val), (self.hor_bound[1], self.val)]

	@dataclass
	class TimeSeries:
		title: str
		series: list = field(default_factory=list)

		def append(self, t, val):
			self.series.append(tuple([t, val]))

		def as_line_x1y1(self):
			return self.series

	def __post_init__(self):
		self.hor_bound = [None, None]
		self.vert_bound = [None, None]

	def _bound_update(self, hor=None, vert=None):
		def lst_udpate(lst, val):
			if val is not None:
				if lst[0] is None:  # First time, huh?
					lst = [val, val]
				else:
					if val < lst[0]:
						lst[0] = val
					elif val > lst[1]:
						lst[1] = val

			return lst

		l = lst_udpate(self.hor_bound, hor)
		self.hor_bound[0] = l[0]
		self.hor_bound[1] = l[1]
		l = lst_udpate(self.vert_bound, vert)
		self.vert_bound[0] = l[0]
		self.vert_bound[1] = l[1]

	def add_l(self, t, op):
		self._bound_update(hor=t)
		self.state[op.id_tuple()]["marks"].append(self.TimePoint("l", self.vert_bound, t))

	def as_iter(self):
		for index, series in self.state.items():
			yield index, [series["trajectory"]] + list(series["marks"])

	def tick(self, t, op):
		index = op.id_tuple()

		if index not in self.state.keys():
			self.state[index] = dict()
			self.state[index]["trajectory"] = self.TimeSeries("trajectory")
			self.state[index]["marks"] = list()
			planned = op.amount_planned
			self.state[index]["marks"].append(self.ValueThreshold("planned", self.hor_bound, planned))

		processed = op.amount_processed
		self.state[index]["trajectory"].append(t, processed)
		self._bound_update(hor=t, vert=processed)

	# Obsolete
	def add_point(self, t, op):
		index = op.id_tuple()

		if index not in self.state.keys():
			self.state[index] = dict()
			self.state[index]["trajectory"] = self.TimeSeries("trajectory")
			self.state[index]["marks"] = list()
			planned = op.sim_env.data_interface.get(op.op_identity.var_amount_planned, **op.op_identity.indices_amount_planned)
			self.state[index]["marks"].append(self.ValueThreshold("planned", self.hor_bound, planned))

		processed = op.op_state.processed_container.amount
		self.state[index]["trajectory"].append(t, processed)
		self._bound_update(hor=t, vert=processed)
		# Log.debug(__file__, self.add_point, "bounds", self.vert_bound, self.hor_bound)


@dataclass
class Log:
	filter_allow: set = None
	filter_disable: set = None
	file: str = None
	level: int = Log.LEVEL

	def check_filter(self, out):
		res = self.filter_allow is None

		if self.filter_allow is not None:
			for s in self.filter_allow:
				if s in out:
					res = True

		if self.filter_disable is not None:
			for s in self.filter_disable:
				if s in out:
					res = res and False

		return res

	LEVEL_SHUT_UP = 0
	LEVEL_CRITICAL = 1
	LEVEL_ERROR = 2
	LEVEL_WARNING = 3
	LEVEL_INFO = 4
	LEVEL_DEBUG = 5
	LEVEL_VERBOSE = 6
	LEVEL = LEVEL_DEBUG  # Default

	def verbose(self, *args, **kwargs):
		if self.level < Log.LEVEL_VERBOSE:
			return

		fmt = self.format(*args, **kwargs)

		if self.check_filter(fmt):
			print("VERBOSE - ", fmt)

	def info(self, *args, **kwargs):
		if self.level < Log.LEVEL_INFO:
			return

		fmt = self.format(*args, **kwargs)

		if self.check_filter(fmt):
			print("INFO - ", fmt)

	def warning(self, *args, **kwargs):
		if self.level < Log.LEVEL_WARNING:
			return

		fmt = self.format(*args, **kwargs)

		if self.check_filter(fmt):
			print("WARN - ", fmt)

	def error(self, *args, **kwargs):
		if self.level < Log.LEVEL_ERROR:
			return

		fmt = self.format(*args, **kwargs)

		if self.check_filter(fmt):
			print("ERROR - ", fmt)

	def debug(self, *args, **kwargs):
		if self.level < Log.LEVEL_DEBUG:
			return

		fmt = self.format(*args, **kwargs)

		if self.check_filter(fmt):
			print("DEBUG - ", fmt)

	def critical(self, *args, **kwargs):
		if self.level < Log.LEVEL_CRITICAL:
			return

		fmt = self.format(*args, **kwargs)

		if self.check_filter(fmt):
			print("CRITICAL - ", fmt)

	def format(self, *args, **kwargs):
		"""
		Formats input data according to the following pattern: "[CONTEXT] TOPICS (if any) | message".

		The context is inferred by detecting the following types of objects:
		- a string representing Path
		- type name
		- callable

		Topics get passed explicitly with `topics=LIST` argument
		"""

		if self.file is not None:
			args = (self.file,) + args

		context = []
		suffix = []

		def is_path(arg):
			if type(arg) is not str:
				return False
			return os.path.isfile(arg) or os.path.isdir(arg)

		def format_path(arg):
			return pathlib.Path(arg).stem

		def is_class(arg):
			return inspect.isclass(arg)

		def format_class(arg):
			return arg.__name__

		def format_callable(arg):
			return str(a).split()[1] + "()"

		for a in args:
			if is_path(a):
				context += [format_path(a)]
			elif is_class(a):
				context += [format_class(a)]
			elif callable(a):
				context += [format_callable(a)]
			else:
				suffix += [str(a)]

		topics = " "
		if "topics" in kwargs.keys():
			topics = kwargs["topics"]
			topics = ' ' + ', '.join(topics) + ' | '

		return '[' + ' : '.join(context) + ']' + topics + ' '.join(suffix)


def module_file_get_abspath(module_file, other_file):
	return str(pathlib.Path(module_file).parent / other_file)
