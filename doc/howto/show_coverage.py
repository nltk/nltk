
import sys, os, re
import nltk.test.coverage as coverage
import color_coverage

OUT_DIR = 'coverage'
MODULE_RE = re.compile(r'nltk.*')

HEAD = (".. ==========================================================\n"
        ".. AUTO-GENERATED LISTING -- DO NOT EDIT!:\n\n"
        ".. role:: red\n"
        "    :class: red\n\n"
        ".. role:: yellow\n"
        "    :class: yellow\n\n"
        ".. role:: green\n"
        "    :class: green\n\n"
        ".. container:: doctest-list\n\n"
        " .. list-table::\n"
        "  :class: doctest-list \n"
        "  :widths: 80 20\n"
        "  :header-rows: 1\n\n"
        "  * - Module\n    - Coverage\n")
FOOT = (".. END AUTO-GENERATED LISTING\n"
        ".. ==========================================================\n")

def report_coverage(module):
    sys.stdout.write('  %-40s ' % module.__name__)
    sys.stdout.flush()
    (fname, stmts, excluded, missing, fmt_missing, def_info) = (
        coverage.analysis3(module))
    out = open(os.path.join(OUT_DIR, module.__name__+'.html'), 'wb')
    color_coverage.colorize_file(fname, module.__name__, out,
                                 fmt_missing, def_info)
    out.close()
    if not missing: c = 100
    elif stmts: c = 100.*(len(stmts)-len(missing)) / len(stmts)
    else: c = 100
    sys.stdout.write('%3d%%\n' % c)
    return c

def init_out_dir():
    # Create the dir if it doesn't exist.
    if not os.path.exists(OUT_DIR):
        os.mkdir(OUT_DIR)

    # Make sure it's actually a dir.
    if not os.path.isdir(OUT_DIR):
        raise ValueError('%s is in the way' % OUT_DIR)

    # Clear its contents.
    for filename in os.listdir(OUT_DIR):
        os.remove(os.path.join(OUT_DIR, filename))

def main(filenames):
    # Collect the coverage data from the given files.
    for filename in filenames:
        cexecuted = coverage.the_coverage.restore_file(filename)
        coverage.the_coverage.merge_data(cexecuted)

    try: init_out_dir()
    except Exception as e:
        print(('Unable to create output directory %r: %s' % (OUT_DIR, e)))
        return

    out = open('coverage-list.txt', 'wb')
    out.write(HEAD)

    # Construct a coverage file for each NLTK module.
    print('\nGenerating coverage summary files...\n')
    print(('  %-40s %s' % ('Module', 'Coverage')))
    print(('  '+'-'*50))
    for module_name, module in sorted(sys.modules.items()):
        if module is None: continue
        if MODULE_RE.match(module_name):
            cover = report_coverage(module)
            if cover == 100: color = 'green'
            elif cover > 50: color = 'yellow'
            else: color = 'red'
            out.write('  * - `%s <%s.html>`__\n'
                      '    - `%d%%`:%s:\n' %
                      (module_name, module_name, cover, color))
            out.flush()
            
    out.write(FOOT)
    out.close()

if __name__ == '__main__':
    main(sys.argv[1:])
