class Mapper:
	def __init__(self):
		pass

	def read_input(self, file):
		for line in file:
		# split the line into words
			yield line.split()
