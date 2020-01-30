import sys
import re

lines = []

with open(sys.argv[1]) as log:
    for line in log.readlines():
        path = re.search(r"^.*:\d", line)
        if path:
            lines.append([path.group(0)])
        else:
            lines[-1].append(line[:-1])

print(lines)
