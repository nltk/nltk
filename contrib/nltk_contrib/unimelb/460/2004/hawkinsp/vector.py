__str__ = '''
433-460 Human Language Technology Project
Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
Student number: 119004

An implementation of a Vector() class for representing MFCC feature vectors.
The class supports several basic vector operations on n-dimensional vectors,
such as addition, subtraction, dot product and scaling.

The python-numeric array class is used instead of Python lists for speed.
Even so, the class is quite slow...

'''

from Numeric import *

class Vector:
    '''A basic n-dimensional Vector class'''
    def __init__(self, val):
        self.value = val

    def __repr__(self):
        return "Vector(%s)" % str(self.value)
        
    def __add__(self, other):
        '''Add two vectors'''

        return Vector(self.value + other.value)
        
    def __sub__(self, other):
        '''Subtract two vectors'''
        return Vector(self.value - other.value)

    def __mul__(self, other):
        '''Form the dot product of two vectors'''
        return sum(self.value * other.value)

    def copy(self):
        '''Produce a copy of a vector'''
        return Vector(array(self.value))

    def scale(self, x):
        '''Scale a vector by a constant factor'''
        self.value = self.value * x

        return self
