import logging
import pathlib
import os
import inspect
import time
import threading

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")


class Log:

	@staticmethod
	def info(*args, **kwargs):
		return logging.info(Log.format(*args, **kwargs))

	@staticmethod
	def warning(*args, **kwargs):
		return logging.warning(Log.format(*args, **kwargs))

	@staticmethod
	def error(*args, **kwargs):
		return logging.error(Log.format(*args, **kwargs))

	@staticmethod
	def debug(*args, **kwargs):
		return logging.debug(Log.format(*args, **kwargs))

	@staticmethod
	def critical(*args, **kwargs):
		return logging.critical(Log.format(*args, **kwargs))

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
			return arg.__name__ + "()"

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
