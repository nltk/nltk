from sexp import *

class FeatureTypeTable(object):
    def __init__(self):
        self.table = {}

    def define_type(self, name, children):
        if name not in self.table.keys():
            self.table[name] = []
        if isinstance(children, basestring):
            children = [children]
        for child in children:
            self.table[name].append(child)

    def subsume(self, name, specialization):
        # quick check if the specialization is the immediate one
        spec = specialization
        if not self.table.has_key(name): return False
        if spec in self.table[name]:
            return True
        return any(self.subsume(item, spec) for item in self.table[name])

    def __repr__(self):
        output = ""
        for key, value in self.table.items():
            output += "%s <--- %s\n" % (key, value)
        return output


if __name__ == "__main__":
    typedefs = open('tests/types.fuf').readlines()
    type_table = FeatureTypeTable()
    for typedef in typedefs:
        sexp = SexpListParser().parse(typedef)
        type_table.define_type(sexp[1], sexp[2])
    print type_table

    print type_table.subsume('np', 'common')
    print type_table.subsume('mood', 'imperative')



