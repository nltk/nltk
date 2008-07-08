class LineOutput:
	""" default output class, output key and value as key'\t'value"""
	@staticmethod
	def collect(key, value):
		separator = '\t'
		keystr = str(key)
		valuestr = str(value)
		print '%s%s%s' % (keystr, separator, valuestr)
