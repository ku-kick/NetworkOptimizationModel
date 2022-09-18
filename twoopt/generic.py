import logging
import pathlib
import os
import inspect
import time
import threading

# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s - %(message)s")


class Log:
	_FILTER_ALLOW = None
	_FILTER_DISABLE = None

	@staticmethod
	def check_filter(out):
		res = Log._FILTER_ALLOW is None

		if Log._FILTER_ALLOW is not None:
			for s in Log._FILTER_ALLOW:
				if s in out:
					res = True

		if Log._FILTER_DISABLE is not None:
			for s in Log._FILTER_DISABLE:
				if s in out:
					res = res and False

		return res

	@staticmethod
	def set_level(level):
		logging.getLogger().setLevel(level)

	@staticmethod
	def info(*args, **kwargs):
		fmt = Log.format(*args, **kwargs)

		if Log.check_filter(fmt):
			return logging.info(fmt)

	@staticmethod
	def warning(*args, **kwargs):
		fmt = Log.format(*args, **kwargs)

		if Log.check_filter(fmt):
			return logging.warning(fmt)

	@staticmethod
	def error(*args, **kwargs):
		fmt = Log.format(*args, **kwargs)

		if Log.check_filter(fmt):
			return logging.error(fmt)

	@staticmethod
	def debug(*args, **kwargs):
		fmt = Log.format(*args, **kwargs)

		if Log.check_filter(fmt):
			return logging.debug(fmt)

	@staticmethod
	def critical(*args, **kwargs):
		fmt = Log.format(*args, **kwargs)

		if Log.check_filter(fmt):
			return logging.critical(fmt)

	@staticmethod
	def format(*args, **kwargs):
		"""
		Formats input data according to the following pattern: "[CONTEXT] TOPICS (if any) | message".

		The context is inferred by detecting the following types of objects:
		- a string representing Path
		- type name
		- callable

		Topics get passed explicitly with `topics=LIST` argument
		"""

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
