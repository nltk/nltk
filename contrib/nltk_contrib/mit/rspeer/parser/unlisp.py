import feature, sys

def process_file(file):
	line = None
	while line != '':
		line = file.readline()
		print process_line(line)

def process_line(line):
	line = line.strip('\n')
	if len(line) == 0: return ''
	if line[0] == ';': return '#' + process_line(line[1:])
	line2 = unlisp(line)
	return makeRule(line2)

def unlisp(expr):
	expr = expr.strip()
	if expr[0] != '(': return expr
	parts = feature.splitWithBrackets(expr[1:-1], " ()")
	return filter(lambda x: x, [unlisp(x) for x in parts])

def makeRule(l):
	if not isinstance(l, list): return l
	return " ".join([makeCat(x) for x in l])

def makeCat(l):
	if l == "==>": l = "->"
	if not isinstance(l, list): return l
	return "%s[%s]" % (l[0], makeFeatures(l[1:]))

def makeFeatures(l):
	if len(l) % 2: raise "Odd number of features and values"
	featlist = []
	for i in range(0, len(l), 2):
		feat = l[i]
		val = l[i+1]
		featlist.append(makeFeature(feat, makeCat(val)))
	return ", ".join(featlist)

def makeFeature(feat, val):
	return "%s %s" % (feat, val)

def main():
	if len(sys.argv) > 1:
		process_file(open(sys.argv[1]))
	else:
		process_file(sys.stdin)

if __name__ == '__main__':
	main()

