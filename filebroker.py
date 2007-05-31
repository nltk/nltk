from urllib import urlretrieve, urlcleanup
import os, re, yaml
from glob import glob

TMPPREFIX = 'tmp_'

class Broker(object):
    
    def __init__(self):
        self.reg_name = 'grammars.yml'
        self.qualifier = 'http://nltk.sourceforge.net/'
        self.reg_qualifier = 'http://nltk.svn.sourceforge.net/viewvc/*checkout*/nltk/trunk/nltk/'
        try:
            reg_localname = self.resolve_filename(self.reg_name, qualifier=self.reg_qualifier, verbose=True)
            #if self.verify(reg_localname):
            self.registry = yaml.load(open(reg_localname))
        except:
            print "Can't find registry"

    #def myreporthook(self, count, block_size, total_size):
        #print total_size
        
    def show_registry(self):
        width = 45
        fns = sorted(self.registry.keys())
        print '=' * width
        print "%-20s %s" % ('Filename', 'Path')
        print '=' * width
        for fn in fns:
            print "%-20s %s" % (fn, self.registry[fn])
        print '=' * width

        
    def verify(self, filehandle):
        """
        
        @ return: input filename or IOError
        """
        er404 = re.compile('404 (Not Found|error)')
        lines = filehandle.readlines()
        for line in lines:
            if er404.search(line):
                print '404'
                #self.empty_cache()
                #print "Locally cached file '%s' has been deleted." % filename
                #raise IOError("The filename '%s' yielded a 404 error." % filename)
        return True
    
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
        try:
            path = self.registry[filename]
            qname = qualifier +path + filename
        except:
            print "Can't find '%s' in registry" % filename
        
        if make_local:
            base = os.path.basename(filename)
            local_fn = TMPPREFIX + base
            if os.path.isfile(local_fn):
                if verbose:
                    print "Using local file '%s' in directory %s" % (local_fn, os.getcwd())
                (fn, header) = urlretrieve(local_fn)
            else:
                if verbose:
                    print "Retrieving '%s' from %s" % (filename, self.qualifier)
                (fn, header) = urlretrieve(qname, local_fn)
        else:
            (fn, header) = urlretrieve(qname)       
            if verbose:
                print "Copying file from the NLTK web site to temp file: '%s'" % fn
                print
                print header
        return fn
    
    def open(self, filename, verbose=False):
        """
        Open a grammar file.
        
        Look first for a local copy of the file. If that doesn't work,
        look up a path for the file from 'grammars.yml', then
        use parse.get_from_sf() to pull the file from the NLTK sourceforge site.
        """
 
        # See if we have a local copy
        try:
            fh = open(filename)
            if verbose:
                print "'%s' was found locally" % filename
        except IOError:
            # Otherwise, try looking up the local path in self.registry
            #path = self.registry[filename]
            #fullname = path + filename
            local = self.resolve_filename(filename, self.reg_qualifier, verbose=verbose)
            print local, os.getcwd()
            fh = open(local)
            #if verbose: 
                #self.show_registry()
            # Maybe the filename has got enough path information already               
            #else:
                #local = filename

            #if verbose:
                #print "Grammar '%s' successfully opened" % local
        if self.verify(fh):
            lines = fh.readlines()
        # check that a file we recovered from SF isn't just a '404 Not Found' page
        fh.close()
        return lines
            
def demo():

    qualifier = 'http://nltk.svn.sourceforge.net/viewvc/*checkout*/nltk/trunk/nltk/'
    b = Broker()
    #print
    #print "Currently cached registry:"
    b.show_registry()
    #print
    b.empty_cache(verbose=True)
    print
    print "Resolving filename with empty cache"
    f = b.resolve_filename('feat0.cfg', qualifier, verbose=True)
    for l in open(f):
        print l,
    #print
    #print "Resolving filename with cache present"
    #b.resolve_filename('feat0.cfg', qualifier, verbose=True)
    #print
    #print "Copy filename from Sourceforge site to temporary file"
    #b.resolve_filename('feat0.cfg', qualifier, make_local=False, verbose=True)
    print
    print b.open('feat0.cfg', verbose=True)
    #b.resolve_filename(b.reg_name, verbose=True)
    #print
    #print "Find grammar file name in 'grammars.yml' and fetch from Sourceforge"
    #g = GrammarFile.read_file("sem3.cfg")
    #print g.grammar()
    ##print
    ##print "Fetch from Sourceforge"   
    ##g = GrammarFile.read_file("examples/semantics/sem3.cfg")
    #print g.grammar()
    #print
    #print "Find locally"   
    #g = GrammarFile.read_file("broker_test.cfg")
    #print g.grammar()
    
if __name__ == '__main__':
    demo()