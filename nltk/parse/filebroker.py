from urllib import urlretrieve, urlcleanup
import os, re, yaml, string
from glob import glob

TMPPREFIX = 'tmp_'

class Broker(object):
    
    def __init__(self, verbose=False):
        #name of the registry file
        self.reg_name = 'grammars.yml'
        
        # root for where to find the grammar files
        self.qualifier = 'http://nltk.sourceforge.net/'
        
        # location for the registry file
        self.reg_qualifier = 'http://nltk.sourceforge.net/examples/'
        
        try:
            reg_localname = self.resolve_filename(self.reg_name, qualifier=self.reg_qualifier, verbose=verbose)
            if self._safe_open(reg_localname):
                self.registry = yaml.load(open(reg_localname))

            #self.registry = yaml.load(self._safe_open(reg_localname))
        except:
            print "Can't find registry '%s at location '%s'" % (self.reg_name, self.reg_qualifier)

        
    def show_registry(self):
        width = 45
        fns = sorted(self.registry.keys())
        print '=' * width
        print "%-20s %s" % ('Filename', 'Path')
        print '=' * width
        for fn in fns:
            print "%-20s %s" % (fn, self.registry[fn])
        print '=' * width

        
    def _safe_open(self, filename):
        """
        
        @return: list(lines) or IOError
        """
        f = open(filename)
        err404 = re.compile('404 (Not Found|error)')
        lines = f.readlines()
        f.close()
        if filter(lambda s: err404.search(s), lines):
                print "The filename '%s' yielded a 404 error." % filename
                os.remove(filename)
                print "Locally cached file '%s' has been deleted from %s." % (filename, os.getcwd())
                return None
        return lines
    
    def empty_cache(self, registry=False, expired=False, verbose=False):
        cwd = os.getcwd()
        tmps = glob(TMPPREFIX + '*')
        cfgs = [fn for fn in tmps if not fn == TMPPREFIX + self.reg_name]
        if registry:
            cached = tmps
        else: cached = cfgs
        if verbose:
            print "Current working directory is:", cwd
            print "Found these cached files:"
            for fn in cached:
                print '   ', fn
            print "Emptying cache..."
        for fn in cached:
            os.remove(fn)
        if verbose:
            print "Done."
        
     
    def resolve_filename(self, filename, qualifier, make_local=True, verbose=False):
        """
        If necessary, make a local copy of a remote file, 
        and return the name of the local copy.
        
        NLTK code which reads grammar files need to know where the grammar
        file is stored. Typically, this location is not in the directory where
        the code is running. This function will check a registry for a path to
        the grammar file. C{urllib.urlretrieve()} returns the name of a
        locally-cached copy of the file, e.g.'/tmp/tmpmgDTlg.cfg'. 
        
        NB, it is possible that the locally-cached file is not what was
        required, but an HTML that wraps an HTTP 404 error message.
        
        @param filename: basename of a file, typically a .cfg grammar file
        @type filename: C{str}
        @param qualifier: URL qualifier
        @type qualifier: C{str}
        @param make_local: if set to C{True}, make the local copy in the 
        current working directory, with the prefix 'tmp_'
        @rtype: C{str}
        @return: name of a locally-cached file
        """
        # Default
        qname = filename
        
        # We're trying to find the registry file
        if filename == self.reg_name:
            qname = qualifier + self.reg_name

        # We're trying to resolve a .cfg file
        elif filename.endswith('.cfg'):
            try:
                # Get the path from the registry
                path = self.registry[filename]
                qualifier = qualifier + path
                qname = qualifier + filename
            except KeyError:
                print "Can't find '%s' in registry" % filename
                # Do we want to put or use a cached file in the current directory?
        else:
            print "Unknown file type: ", filename
            return None
    
        if make_local:
            base = os.path.basename(filename)
            local_fn = TMPPREFIX + base
            # Do we already have a cached copy?
            if os.path.isfile(local_fn):
                if verbose and not filename == self.reg_name:
                    print "Re-using cached file '%s' in directory %s" % (local_fn, os.getcwd())
                (fn, header) = urlretrieve(local_fn)
            # Otherwise, fetch it from the NLTK SF web site
            else:
                if verbose:
                    print "I'll try to retrieve '%s' from %s" % (filename, qualifier)
                try:
                    (fn, header) = urlretrieve(qname, local_fn)
                except IOError:
                    print "Sorry, I can't find '%s' at %s:" % (filename, self.reg_qualifier)
                    return None
        # We still have to fetch the file, but we'll put in /tmp or similar
        else:
            try:
                (fn, header) = urlretrieve(qname)
                if verbose:
                    print "I'll try to copy the file from the NLTK web site to temp file: '%s'" % fn
                    print
                    print 'Header file:'
                    print '------------'
                    print header
            except IOError:
                    print "Sorry, I can't find '%s' at %s:" % (filename, self.reg_qualifier)
                    return None
            
        return fn
    
    def open(self, filename, verbose=False):
        """
        Open a grammar file.
        
        Look first for a local copy of the file. If that doesn't work,
        look up a path for the file from 'grammars.yml', then
        use parse.get_from_sf() to pull the file from the NLTK sourceforge site.
        
        @param filename: grammar file to be opened
        @return: the result of applying C{readlines()} to the opened file.
        @rtype: C{list(str)}
        """
 
        # See if we have a local copy
        try:
            f = open(filename)
            lines = f.readlines()
            f.close()
            if verbose:
                print "File '%s' was found locally" % filename
            return lines
        except IOError:
            # Otherwise, try looking up the local path in self.registry
            # and try to get a valid locally-cached copy
            cached = self.resolve_filename(filename, self.qualifier, verbose=verbose)
            if cached :
                if verbose:
                    print "I found '%s' in the directory %s" % (cached, os.getcwd())
                lines = self._safe_open(cached)
                if verbose:
                    print "Grammar file '%s' was successfully opened" % cached
                    for l in lines:
                        print l,
                return lines
            else:
                print "Failed to open file '%s'." % filename
                return None

    
def load(filename, verbose=False):
    """
    Wrapper to call the C{open()} method of a Broker instance.
    """
    b = Broker()
    return b.open(filename, verbose=verbose)

def pprint(filename, escape='##'):
    for l in load(filename):
        if l.startswith(escape): continue
        if re.match('^$', l): continue
        
        print l,
            
def demo():

    qualifier = 'http://nltk.sourceforge.net/'
    b = Broker()
    print
    print "Currently cached registry:"
    b.show_registry()
    print
    b.empty_cache(verbose=True)
    print
    print "Resolving filename with empty cache:"
    b.resolve_filename('feat0.cfg', qualifier, verbose=True)
    print
    print "Resolving filename with cache present:"
    b.resolve_filename('feat0.cfg', qualifier, verbose=True)
    print
    print "Copy filename from Sourceforge site to temporary file:"
    b.resolve_filename('feat0.cfg', qualifier, make_local=False, verbose=True)
    print 
    print "Delete the locally-cached registry file:"
    b.empty_cache(registry=True, verbose=True)
    b = Broker()
    print
    print "Open a file:"
    load('feat0.cfg', verbose=True)
    print
    print "Pretty-print a file:"
    pprint('feat0.cfg')
    print
    print "Try to find a file that doesn't exist:"
    load('missing.cfg', verbose=True)
    print
    print "Find locally:"   
    load("broker_test.cfg", verbose=True)
    print
    print "Time to clean up"
    b.empty_cache(registry=True, verbose=True)

    
if __name__ == '__main__':
    demo()

