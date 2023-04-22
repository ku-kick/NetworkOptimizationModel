import dataclasses


@dataclasses.dataclass
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
