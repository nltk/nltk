#
# Natural Language Toolkit: Hidden Markov Model extensions
#
# Copyright (C) 2004 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$
#

"""
Build scripts for the local Pyrex modules. Run:
    python setup.py build_ext --inplace
to build the shared objects for your platform. One module requires a PowerPC
processor, so you may need to edit this file.
"""

from distutils.core import setup
from distutils.extension import Extension
from Pyrex.Distutils import build_ext

sc_ext = Extension("standard_c", ["standard_c.pyx"],
    extra_compile_args=['-O2'])

vl_ext = Extension("veclib", ["veclib.pyx"], 
    include_dirs=["/System/Library/Frameworks/vecLib.framework/Headers/",
                  "/System/Library/Frameworks/Accelerate.framework/Headers/"],
    extra_compile_args=['-faltivec', '-O2'],
    extra_link_args=['/System/Library/Frameworks/Accelerate.framework/Accelerate', 
                     '-faltivec'])

setup(
    name = "Hidden Markov Model optimisations",
    ext_modules=[sc_ext, vl_ext],
    cmdclass = {'build_ext': build_ext}
)

