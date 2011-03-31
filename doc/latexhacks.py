#!/usr/bin/env python
# Post-process latex output in-place

import sys
import re

# load the file
file = open(sys.argv[1])
contents = file.read()
file.close()

# modify it
contents = re.sub(r'subsection{', r'subsection*{', contents)

# save the file
file= open(sys.argv[1], 'w')
file.write(contents)
file.close()
