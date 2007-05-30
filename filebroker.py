from urllib import urlretrieve, urlcleanup
import os, re, yaml

TMPPREFIX = 'tmp_'

class Broker(object):
    
    def __init__(self):
        self.reg_name = 'grammars.yml'
        self.qualifier = 'http://nltk.sourceforge.net/'
        self.reg_qualifier = 'http://nltk.svn.sourceforge.net/viewvc/*checkout*/nltk/trunk/nltk/examples/'
        try:
            reg_localname = self.resolve_filename(self.reg_name, qualifier=self.reg_qualifier, verbose=True)
            if self.verify(reg_localname):
                self.registry = yaml.load(open(reg_localname))
        except:
            self.registry = {}

    #def myreporthook(self, count, block_size, total_size):
        #print total_size
        
    def verify(self, filename):
        """
        
        @ return: input filename or IOError
        """
        er404 = re.compile('404 (Not Found|error)')
        lines = open(filename).readlines()
        for line in lines:
            if er404.search(line):
                os.remove(filename)
                print "Locally cached file '%' has been deleted." % filename
                raise IOError("The filename '%s' yielded a 404 error." % filename)
        return True
     
    def resolve_filename(self, filename, qualifier, make_local=True, verbose=True):
        """
        Fetch a file from the NLTK site on Sourceforge.
        
        urllib.urlretrieve() returns the name of a locally-cached 
        copy of the file, e.g.'/tmp/tmpmgDTlg.cfg'. Note that ViewVC
        doesn't raise an HTTP 404 error if the file can't be found, but
        wraps the error in a valid HTML page.
        
        @ rtype: C{str}
        @ return: name of a valid local file (possibly cached)
        """
        #qualifier = self.qualifier
        qname = qualifier + filename
        if make_local:
            base = os.path.basename(filename)
            local_fn = TMPPREFIX + base
            if os.path.isfile(local_fn):
                if verbose:
                    print "Using local file: '%s'" % local_fn
                (fn, header) = urlretrieve(local_fn)
            else:
                if verbose:
                    print "Retrieving '%s' from %s" % (filename, self.qualifier)
                (fn, header) = urlretrieve(qname, local_fn)
        else:
            (fn, header) = urlretrieve(qname)       
            if verbose:
                print "Using temporary file: '%s'" % fn
        return fn
    
    @staticmethod
    def open(filename, verbose=True):
        """
        Open the grammar file.
        
        Look first for a local copy of the file. If that doesn't work,
        look up a path for the file from 'grammars.yml', then
        use parse.get_from_sf() to pull the file from the NLTK sourceforge site.
        """
 
        # See if we have a local copy

        try:
            f = open(filename)
            if verbose:
                print "'%s' was found locally" % filename
        except IOError:
            # Otherwise, try looking up the local path in self.registry, if it's been recovered
            # Try to recover an index of the grammar files from Sourceforge 
            try:
                remote_fn = self.resolve_filename(self.reg_name, qualifier = self.reg_qualifier, verbose=verbose)
                self.verify(remote_fn)
                self.registry = yaml.load(open(remote_fn))
                if verbose and self.registry:
                    print "Registry has the following entries:"
                    for key in self.registry: 
                        print "%s\tlocated at %s" % (key, self.registry[key])
            except IOError:
                pass
            if filename in self.registry:
                path = self.registry[filename]
                local = path + filename
            # Maybe the filename has got enough path information already               
            else:
                local = filename
            f = open(get_from_sf(local, verbose=verbose))
            if verbose:
                print "Grammar '%s' successfully opened" % local
        lines = f.readlines()
        # check that a file we recovered from SF isn't just a '404 Not Found' page
        
        self.apply_lines(lines)
        f.close()
            
def demo():

    b = Broker()
    print b.registry
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