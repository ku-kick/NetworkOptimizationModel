
def iter_plain(root):
	try:
		for i in root:
			yield from iter_plain(i)
	except TypeError:
		yield root
