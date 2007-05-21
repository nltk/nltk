import re

def convert_data(file_path, ext, suffix = 'conv'):
    lines = []
    f = open(file_path, 'r')
    for line in f:        
        words = line.split()
        words = words[1:] + [words[0]]
        lines.append(','.join(words))
    f.close()
    ext_dot_index = file_path.rindex('.')
    if ext_dot_index == -1:
        base_name = file_path
    else:
        base_name = file_path[:ext_dot_index]
    f = open((base_name + suffix) + '.' + ext, 'w')
    for line in lines:
        f.write(line + '\n')
    f.close()    
    
def values(file_path, index):
    values = []
    f = open(file_path, 'r')
    for line in f:        
        words = line.split()
        values.append(words[index])
    return ','.join(values)
    
        