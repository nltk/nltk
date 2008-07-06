"""
express objects in string format, 
and infer object type from string expression
"""

def obj2str(obj):
	"""
	different object will be appended different postfix
	>>> obj2str(1)
	'1@i'
	>>> obj2str(1.2)
	'1.2@f'
	>>> obj2str("word")
	'word@s'
	>>> obj2str((1,2))
	Traceback (most recent call last):
	...
	ValueError: The object must be either int, float or str
	"""
	if isinstance(obj, int):
		return str(obj) + '@i'
	elif isinstance(obj, float):
		return str(obj) + '@f'
	elif isinstance(obj, str):
		return obj + '@s'
	else:
		raise ValueError, "The object must be either int, float or str"

def str2obj(str):
	"""
	convert the string representation to the original object
	>>> str2obj("20@i")
	20
	>>> str2obj("20.0@f")
	20.0
	>>> str2obj("word@s")
	'word'
	>>> str2obj("word")
	Traceback (most recent call last):
	...
	ValueError: Cannot infer the object type
	"""
	flag = str[-2:]
	if flag == '@i':
		return int(str[:-2])
	elif flag == '@f':
		return float(str[:-2])
	elif flag == '@s':
		return str[:-2]
	else:
		raise ValueError, "Cannot infer the object type"


if __name__ == "__main__":
	import doctest 
	doctest.testmod()
