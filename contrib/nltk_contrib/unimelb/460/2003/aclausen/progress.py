import time
import sys

STOPPED = 0
STARTED = 1

# Abstract class... override handle()
class ProgressTimer:
	def __init__(self, task=''):
		self.reset()
		self.set_task(task)
		self.handle_time = 0

	def handle(self):
		assert 0, "override me"

	def do_handle(self):
		if (self.handle_time <= self.update_time - 1
				or self.frac_done == 1.0):
			self.handle_time = self.update_time
			self.handle()

	def set_task(self, task=''):
		self.task = task

	def get_task(self):
		return self.task

	def reset(self):
		global STOPPED
		self.state = STOPPED
		self.frac_done = 0
		self.total_prior_time = 0

	def start(self):
		global STOPPED, STARTED
		assert self.state == STOPPED
		self.state = STARTED
		self.start_time = time.time()
		self.update_time = self.start_time

	def stop(self):
		global STOPPED, STARTED
		assert self.state == STARTED
		self.total_prior_time += time.time() - self.start_time

	def update(self, frac_done):
		self.frac_done = frac_done
		self.update_time = time.time()
		self.do_handle()

	def total_time_spent(self):
		return self.total_prior_time + time.time() - self.start_time

	def predicted_total_time(self):
		if self.frac_done == 0:
			return 0
		else:
			return self.total_time_spent() / self.frac_done

	def predicted_time_left(self):
		if self.frac_done == 0:
			return 0
		else:
			return self.total_time_spent() * (1 - self.frac_done) / self.frac_done

class SimpleTimer(ProgressTimer):
	def handle(self):
		eta = self.predicted_time_left()
		sys.stdout.write( '\r%s: %.1f%% (ETA %d:%02d:%02d)' % (
				self.task,
				100 * self.frac_done,
				int(eta / 60 / 60),
				int(eta / 60 % 60),
				int(eta) % 60) )
		sys.stdout.flush()

