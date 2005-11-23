#----------------------------------------------------------------------------#
# progressBar.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Thu Feb 10 12:25:51 EST 2005
#
#----------------------------------------------------------------------------#

import sys
import time

class ProgressBar:
	""" A progress bar which gets printed to stdout.
	"""
	def __init__(self, stringSize=20):
		""" Creates a new instance, setting the size as needed.
		"""
		self.__stringSize = stringSize
		self.__count = 0
		self.__totalCount = None
		self.__lastLineSize = None
		self.__lastRotation = 0
		self.__startTime = None

		self.__rotation = ['/', '-', '\\', '|']
		self.__numRotations = len(self.__rotation)

		return

	def reset(self):
		""" Resets the progress bar to initial conditions.
		"""
		self.__count = 0
		self.__totalCount = None
		self.__lastLineSize = None
		self.__lastRotation = 0
		self.__startTime = None

		return
	
	def start(self, totalCount):
		""" Starts the progress bar. This will be the first output from the
			bar. At this stage it needs the total count so that it can
			calculate percentages.

			@param totalCount: The count which represents 'finished'.
		"""
		assert self.__count == 0, "Progress bar already started, call reset()"
		assert totalCount > 0, "Progress bar needs a non-zero total count"
		self.__totalCount = totalCount
		progressLine = '[/' + (self.__stringSize-1)*' ' + ']   0%'
		sys.stdout.write(progressLine)
		sys.stdout.flush()
		self.__lastLineSize = len(progressLine)

		self.__startTime = time.time()

		return

	def update(self, count):
		""" Updates the progress bar with the current count. This is useful
			to call even if the count has not increased, since it provides
			visual feedback to the user that the process is active.

			@param count: The current count
		"""
		count = int(count)
		assert count >= 0 and count <= self.__totalCount
		n = (count * self.__stringSize) / self.__totalCount
		percent = (100*count) / self.__totalCount
		m = self.__stringSize - n - 1 # subtract one for the rotating char

		self.__lastRotation = (self.__lastRotation + 1) % self.__numRotations
		if percent < 100:
			rotChar = self.__rotation[self.__lastRotation]
		else:
			rotChar = ''

		progressLine = '[' + n*'-' + rotChar + m*' ' + \
				str('] %3d%%' % percent)
		sys.stdout.write('\b'*(self.__lastLineSize))
		sys.stdout.write(progressLine)
		sys.stdout.flush()
		self.__lastLineSize = len(progressLine)

		return

	def fractional(self, fraction):
		""" Set a fractional percentage completion, e.g. 0.3333 -> 33%.
		"""
		assert fraction >= 0 and fraction <= 1
		self.update(int(fraction * self.__totalCount))

		return
	
	def finish(self):
		""" Fixes to 100% complete, and writes the time taken.
		"""
		assert self.__totalCount > 0, "Progress bar wasn't initialised"
		self.update(self.__totalCount)

		timeTaken = int(time.time() - self.__startTime)
		(mins, secs) = divmod(timeTaken, 60)
		if not mins:
			timeString = ' (%ds)\n' % secs
		else:
			(hours, mins) = divmod(mins, 60)
			if not hours:
				timeString = ' (%dm %ds)\n' % (mins, secs)
			else:
				timeString = ' (%dh %dm %ds)\n' % (hours, mins, secs)

		sys.stdout.write(timeString)

		# precautionary, in case finish() is called more than once
		self.__lastLineSize += len(timeString)

		return

