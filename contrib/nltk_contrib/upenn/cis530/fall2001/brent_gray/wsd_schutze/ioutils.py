##  ioutils.py
##  input/output utilities for word sense discrimination project
##  Brent Gray -- CIS 530


import re
def wordRead(_f, direction):
    """
    reads a single word, and consumes, searching
    in the direction indicated by the parameter direction:
    namely, -1 for backwards, 1 for forwards.  It is the responsibility
    of the caller to keep track of the current position in the file -- this
    function moves the pointer
    """

    def movePointer(__f, _direction):
        returnValue = 1
        if (_direction == -1):
            if (__f.tell() -2 >= 0):
                __f.seek(-2, 1)
                return 1
            else:  ## no more characters left!
                return 0
        else:
            ##  don't do anything, b/c _f.read(1) will move pointer for us
            return 1
    
    buffer = ''
    whiteSpaceRE = re.compile(r'[\s+\W+]')
    characterRE = re.compile(r'\w+')
    if (movePointer(_f, direction)):
        char = _f.read(1)
    else:
        return 'unk'
    while whiteSpaceRE.match(char):
        if (movePointer(_f, direction)):
            char = _f.read(1)
        else:
            return 'unk'
    while characterRE.match(char):
        if (direction == -1):
            buffer = char + buffer
        else:
            buffer = buffer + char
        if (movePointer(_f, direction)):
            char = _f.read(1)
        else:
            return 'unk'
    if len(buffer) >= 1:
        return buffer
    else:
        return 'unk'


def timer(command):
    startTime = time.time()
    exec command
    stopTime = time.time()
    print 'Elapsed Time:  %.3f seconds' % (stopTime - startTime)
