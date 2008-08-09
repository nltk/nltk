"""
express tuples in string format, 
and recover tuples from string expression
"""

def tuple2str(t, separator = ' '):
	"""
	convert tuple into string expression

	>>> tuple2str((1, 2))
	'1 2'
	>>> tuple2str((1, "word"), '#')
	'1#word'
	>>> tuple2str(1)
	Traceback (most recent call last):
	...
	ValueError: The first parameter must be a tuple
	"""
	if isinstance(t, tuple):
		s = ""
		for e in t[:-1]:
			s += str(e) + separator
		s += str(t[-1])

		return s
	else:
		raise ValueError, "The first parameter must be a tuple"

def str2tuple(s, separator = ' '):
	"""
	convert the string representation to a tuple

	>>> str2tuple("20 3")
	('20', '3')
	>>> str2tuple("hello#world", '#')
	('hello', 'world')
	>>> str2tuple(1)
	Traceback (most recent call last):
	...
	ValueError: the first parameter must be a string
	"""
	if isinstance(s, str):
		t = s.strip().split(separator)
		return tuple(t)
	else:
		raise ValueError, "the first parameter must be a string"


if __name__ == "__main__":
	import doctest 
	doctest.testmod()
