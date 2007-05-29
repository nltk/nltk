from featurechart import *
from logic import Counter
import sys

def interact(grammar_filename, trace=2):
    cp = load_earley(grammar_filename, trace=trace-2)
    model = []
    counter = Counter()
    while True:
        sys.stdout.write('> ')
        line = sys.stdin.readline().strip()
        if not line: break

        # Read a line and parse it.
        trees = cp.parse(line)
        if len(trees) == 0:
            print "I don't understand."
            continue
        elif len(trees) > 1:
            print "That was ambiguous, but I'll guess at what you meant."
        
        # Extract semantic information from the parse tree.
        tree = trees[0]
        pos = tree[0][0].node['pos']
        sem = tree[0].node['sem']

        # We need variables to have unique names even if they didn't get
        # alpha-converted already. Replace all the variables that are unbound
        # via skolemization -- but not the ones that are completely free,
        # like "mary" -- with uniquely-named ones.
        free = sem.free()
        skolem = sem.skolemize()
        almostfree = skolem.free()
        vars = set(almostfree).difference(free)
        for var in vars:
            skolem = skolem.replace_unique(var, counter)
        
        if trace > 0:
            print tree
            print 'Semantic value:', skolem
        clauses = skolem.clauses()
        if trace > 1:
            print "Got these clauses:"
            for clause in clauses:
                print '\t', clause
        
        if pos == 'S':
            # Handle statements
            model += clauses
        elif pos == 'Q':
            # Handle questions
            bindings = {}
            success = True
            for clause in clauses:
                success = False
                for known in model:
                    newbindings = dict(bindings)
                    try:
                        unify(object_to_features(clause),
                        object_to_features(known), newbindings)
                        bindings = newbindings
                        success = True
                        break
                    except UnificationFailure:
                        continue
                if not success:
                    break
            if success:
                # answer 
                answer = bindings.get('wh', 'Yes.')
                print answer['variable']['name']
            else:
                # This is an open world without negation, so negative answers
                # aren't possible.
                print "I don't know."

def demo():
    interact('lab3-slash.cfg', trace=2)

if __name__ == '__main__':
    demo()

