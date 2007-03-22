from featurechart import *
from treeview import *

def demo():
    cp = load_earley('gazdar4.cfg')
    trees = cp.parse('which guy does Mary see')
    TreeView(trees)

def run_profile():
    import profile
    profile.run('for i in range(1): demo()', '/tmp/profile.out')
    import pstats
    p = pstats.Stats('/tmp/profile.out')
    p.strip_dirs().sort_stats('time', 'cum').print_stats(60)
    p.strip_dirs().sort_stats('cum', 'time').print_stats(60)

#run_profile()
demo()
