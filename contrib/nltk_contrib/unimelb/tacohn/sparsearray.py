import Numeric

def dot(array1, array2):
    try: return array1.dot(array2)
    except AttributeError:
        try: return array2.dot(array1)
        except AttributeError:
            return Numeric.dot(array1, array2)

def sum(array):
    try:
        assignments = array.assignments()
        s = array.default() * (len(array) - len(assignments))
        for index, value in assignments:
            s += value
        return s
    except AttributeError:
        return Numeric.sum(array)

class SparseArray:
    def __init__(self, dimensions, default=0, assignments=None):
        self._default = default
        if assignments:
            self._assignments = assignments.copy()
        else:
            self._assignments = {}

        try:
            self._n = len(dimensions)
            self._assignments = {}
            for i in range(self._n):
                value = dimensions[i]
                if value != self._default:
                    self._assignments[i] = value
        except TypeError:
            self._n = dimensions

    def assignments(self):
        return self._assignments.items()

    def default(self):
        return self._default

    def as_dense_array(self):
        return Numeric.array(self)

    def dot(self, other):
        assert len(self) == len(other)
        v = 0
        try:
            indices = dict(self._assignments)
            indices.update(other._assignments)
            v += (len(self) - len(indices)) * (self._default * other._default)
            for index in indices.keys():
                v += self[index] * other[index]
        except AttributeError:
            for i in range(len(self)):
                v += self[i] * other[i]
        return v

    def matrix_multiply(self, matrix):
        shape = matrix.shape
        assert shape[0] == len(self)
        v = SparseArray(self._n, self._default)
        for i in range(len(self)):
            v[i] = self.dot(matrix[:,i])
        return v

    def matrix_multiply_transpose(self, matrix):
        shape = matrix.shape
        assert shape[1] == len(self)
        v = SparseArray(self._n, self._default)
        for i in range(len(self)):
            v[i] = self.dot(matrix[i])
        return v

    def as_dense_array(self):
        return Numeric.array(self)

    def add_to(self, dense_array):
        if self._default:
            for index in range(len(self)):
                dense_array[index] += self[index]
        else:
            for index, value in self._assignments.items():
                dense_array[index] += value

    def subtract_from(self, dense_array):
        if self._default:
            for index in range(len(self)):
                dense_array[index] -= self[index]
        else:
            for index, value in self._assignments.items():
                dense_array[index] -= value

    def __len__(self):
        return self._n

    def __getitem__(self, i):
        if i >= 0 and i < self._n:
            return self._assignments.get(i, self._default)
        else:
            raise IndexError('index out of range')

    def __setitem__(self, i, v):
        if i >= 0 and i < self._n:
            if v != self._default:
                self._assignments[i] = v
            elif self._assignments.has_key(i):
                del self._assignments[i]
        else:
            raise IndexError('index out of range')

    def __add__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise addition using sparse vectors
                v = SparseArray(self._n, self._default + other._default)
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    v[index] = self[index] + other[index]
            except AttributeError:
                # do an element-wise addition with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                v = SparseArray(self._n, self._default)
                for index in range(len(self)):
                    v[index] = self[index] + other[index]
        except TypeError:
            # addition with a scalar
            v = SparseArray(self._n, self._default + other)
            for index, value in self._assignments.items():
                v[index] = self[index] + other
        return v

    def __div__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise division using sparse vectors
                v = SparseArray(self._n, self._default / other._default)
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    v[index] = self[index] / other[index]
            except AttributeError:
                # do an element-wise division with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                v = SparseArray(self._n, self._default)
                for index in range(len(self)):
                    v[index] = self[index] / other[index]
        except TypeError:
            # divide by a scalar
            v = SparseArray(self._n, self._default / other)
            for index, value in self._assignments.items():
                v[index] = self[index] / other
        return v

    def __mul__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise multiplication using sparse vectors
                v = SparseArray(self._n, self._default * other._default)
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    v[index] = self[index] * other[index]
            except AttributeError:
                # do an element-wise multiplication with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                v = SparseArray(self._n, self._default)
                for index in range(len(self)):
                    v[index] = self[index] * other[index]
        except TypeError:
            # multiply by a scalar
            v = SparseArray(self._n, self._default * other)
            for index, value in self._assignments.items():
                v[index] = self[index] * other
        return v

    def __sub__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise subtraction using sparse vectors
                v = SparseArray(self._n, self._default - other._default)
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    v[index] = self[index] - other[index]
            except AttributeError:
                # do an element-wise subtraction with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                v = SparseArray(self._n, self._default)
                for index in range(len(self)):
                    v[index] = self[index] - other[index]
        except TypeError:
            # subtract a scalar
            v = SparseArray(self._n, self._default - other)
            for index, value in self._assignments.items():
                v[index] = self[index] - other
        return v

    def __pow__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise power using sparse vectors
                v = SparseArray(self._n, self._default ** other._default)
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    v[index] = self[index] - other[index]
            except AttributeError:
                # do an element-wise power with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                v = SparseArray(self._n, self._default)
                for index in range(len(self)):
                    v[index] = self[index] ** other[index]
        except TypeError:
            # to power of a scalar
            v = SparseArray(self._n, self._default ** other)
            for index, value in self._assignments.items():
                v[index] = self[index] ** other
        return v

    def __iadd__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise addition using sparse vectors
                self._default += other._default
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    self[index] += other[index]
            except AttributeError:
                # do an element-wise addition with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                for index in range(len(self)):
                    self[index] += other[index]
        except TypeError:
            # addition with a scalar
            self._default += other
            for index in self._assignments.keys():
                self[index] += other
        return self

    def __isub__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise subtraction using sparse vectors
                self._default -= other._default
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    self[index] -= other[index]
            except AttributeError:
                # do an element-wise subtraction with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                for index in range(len(self)):
                    self[index] -= other[index]
        except TypeError:
            # subtraction with a scalar
            self._default -= other
            for index in self._assignments.keys():
                self[index] -= other
        return self

    def __imul__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise multiplication using sparse vectors
                self._default *= other._default
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    self[index] *= other[index]
            except AttributeError:
                # do an element-wise multiplication with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                for index in range(len(self)):
                    self[index] *= other[index]
        except TypeError:
            # multiply by a scalar
            self._default *= other
            for index in self._assignments.keys():
                self[index] *= other
        return self

    def __idiv__(self, other):
        try:
            assert len(self) == len(other)
            try:
                # do an element-wise division using sparse vectors
                self._default /= other._default
                indices = dict(self._assignments)
                indices.update(other._assignments)
                for index in indices.keys():
                    self[index] /= other[index]
            except AttributeError:
                # do an element-wise division with a sequence
                # [FIXME] - v prolly shouldn't be sparse, but need to [:] or
                # copy to interface with sequences and Numeric arrays
                for index in range(len(self)):
                    self[index] /= other[index]
        except TypeError:
            # division by a scalar
            self._default /= other
            for index in self._assignments.keys():
                self[index] /= other
        return self

    def __getslice__(self, start, end):
        start = min(max(start, 0), self._n)
        end = min(max(end, 0), self._n)
        if end > start:
            v = SparseArray(end - start, self._default)
            for index in self._assignments.keys():
                if start <= index < end:
                    v[index - start] = self._assignments[index]
            return v
        else:
            return []

    def __setslice__(self, start, end, values):
        start = min(max(start, 0), self._n)
        end = min(max(end, 0), self._n)
        assert len(values) == end - start, 'Cannot resize vector'
        for i in range(len(values)):
            self[start + i] = values[i]

    def __str__(self):
        return '[%s]' % ', '.join(map(str, self))

    def __repr__(self):
        return 'SparseArray(%d, %s, %s)' % (self._n, self._default,
                    self._assignments)

    __radd__ = __add__
    __rmul__ = __mul__
    __rdiv__ = __div__
    # order of operations important for these
    #__rsub__ = __sub__ 
    #__rpow__ = __pow__

def test():
    a = SparseArray(5, 1)
    a[0] = 10
    a[3] = 2
    print str(a), `a`
    a *= 2
    print str(a), `a`
    a += 2
    print str(a), `a`
    a /= range(1, 6)
    print str(a), `a`
    b = SparseArray(5, 3, {2:15})
    a -= b
    print str(a), `a`
    print a.dot(b), b.dot(a)
    print a.as_dense_array()
    M = Numeric.array(range(25)).resize((5,5))
    print a.matrix_multiply(M)
    print Numeric.matrixmultiply(a.as_dense_array(), M)
    print a.matrix_multiply_transpose(M)
    print Numeric.matrixmultiply(M, a.as_dense_array())
    c = SparseArray([1,2,3,4,5])
    print c, `c`

if __name__ == '__main__':
    test()


