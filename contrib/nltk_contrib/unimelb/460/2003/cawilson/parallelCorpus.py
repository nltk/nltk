# 433-460 Project
# 
# Author: Charlotte Wilson (cawilson)
# Date: October 2003
#
# Parallel Corpus Reader module:
#
# ParallelCorpusReader extends the SimpleCorpusReader module form nltk. 
# For further information see the documentation for the nltk corpus module.
"""
Access to parallel corpora used in the project. Each corpus is
accessed by an instance of a CorpusReader class. The following corpus
readers are defined:

  -  de-news: A collection of approximately 10,000 German daily news items, 
     taken from German radio news broadcasts which have been (human) 
     translated into English. These news items have been processed 
     into a format suitable for machine translation, including 
     one-to-one sentence alignment. For  more information see:
     www.isi.edu/~koehn/publications/de-news/

  - europarl: A collection of transcripts of the European parliamentary 
    proceedings between 1998 and 2001. This corpus contains 1 file per 
    language per day and has been processed into a format suitable for
    machine translation, including one-to-one sentence alignment. For more 
    information see: www.isi.edu/~koehn/publications/europarl/
"""

# Path variables specifying the locations of the corpora - 
europarl_path = "/home/pgrad/tacohn/corpora/de-en"
de_news_path = "/home/hons/cawilson/corpus/de_news/txt"


from nltk.corpus import *

##########################################################################

class ParallelCorpusReader1(SimpleCorpusReader):
	"""
	This module contains functions to access a parallel corpus, 
	which is composed of a number of corresponding files 
	(1 per language). These files have with corresponding names 
	differing only by a 'langauge suffix' and/or a language directory name. 

	For example the filenames 
	'de-news-1999-10-10.en.al' and 'de-news-1999-10-10.de.al'
	correspond in the de-news parallel corpus where 'en' is the 
	English language suffix and 'de' is the German language suffix 
	on the file-name.

	For further information see the documentation for SimpleCorpusReader.
	"""

	def __init__(self,
                 	# Basic Information
                 	name, rootdir, items_regexp, 
			lang_suffixes, file_suffix, 
                 	# Grouping
                 	groups=None,
                 	# Meta-data
                 	description=None, description_file=None, 
                 	license_file=None,
                 	copyright_file=None,
                 	# Formatting meta-data
                	default_tokenizer=WSTokenizer()):
		"""
		Construct a new corpus parallel corpus reader. Based on the 
		constructor for SimpleCorpusReadrer in nltk corpus module, 
		modified to include a list of C{lang_filenames} (1 per 
		language) and a C{file_suffix}.  A filename in the parallel 
		corpus is given by concatenating the C{item_regeexp}, 
		the C{lang_suffix} and the C{file_suffix}.
		
		The parameters C{description}, C{description_file}, 
		C{license_file}, and C{copyright_file} specify optional 
		metadata. For the parallel corpus reader's description, you 
		should use C{description} or C{description_file}, but not both.

        	@group Basic Information: name, rootdir, items_regexp, 
			lang_suffixes, file_suffix
       		@group Grouping: groups
        	@group Meta-data: description, license, copyright,
            		description_file, license_file, copyright_file
        	@group Formatting Meta-data: default_tokenizer

	        @type name: C{string}
       		@param name: The name of the corpus.  This name is used for
            		printing the corpus reader, and for constructing
	    		locations.  It should usually be identical to the 
			name of the variable that holds the corpus reader.
        	@type rootdir: C{string}
        	@param rootdir: The path to the root directory for the
            		corpus.  If C{rootdir} is a relative path, then it is
            		interpreted relative to the C{nltk.corpus} base 
			directory (as returned by L{nltk.corpus.get_basedir()}).
        	@type items_regexp: C{regexp} or C{string}
        	@param items_regexp: A regular expression over paths that
            		defines the set of files that should be listed as
            		entities for the corpus.  The paths that this is tested
            		against are all relative to the corpus's root directory.
            		Use the forward-slash character (C{'/'} to delimit
            		subdirectories; C{SimpleCorpusReader} will 
			automatically convert this to the appropriate path 
			delimiter for the operating system.
		@type lang_suffixes: C{List} of C{string}
		@param lang_suffixes: A list of the file extensions that 
			indicate the language of the file. e.g. '.en' for 
			English files, '.de' for German files. A language file 
			extension should include a fullstop, if necessary and 
			may be followed by a C{file_suffix}. 
		@type file_suffix: C{string}
		@param file_suffix: A string giving the file extension for 
			the files that should be listed as entities in the 
			parallel corpus. This file extension is the final 
			suffix on the filename and should include a fullstop, 
			if necessary.
        	@type groups: C{list} of C{(string, regexp)} tuples
        	@param groups: A list specifying the groups for the corpus.
            		Each element in this list should be a pair
            		C{(M{groupname}, M{regexp})}, where C{M{groupname}} 
			is the name of a group; and C{M{regexp}} is a regular
			expression over paths that defines the set of files 
			that should be listed as entities for that group.  
			The paths that these regular expressions are tested 
			against are all relative to the corpus's root 
			directory.  Use the forward-slash character (C{'/'} to 
			delimit subdirectories; C{SimpleCorpusReader} will 
			automatically convert this to the appropriate path 
			delimiter for the operating system.
        	@type description: C{string}
        	@param description: A description of the corpus.
        	@type description_file: C{string}
		@param description_file: The path to a file containing a
            		description of the corpus.  If this is a relative path,
            		then it is interpreted relative to the corpus's root
            		directory.
        	@type license_file: C{string}
        	@param license_file: The path to a file containing licensing
            		information about the corpus.  If this is a relative
            		path, then it is interpreted relative to the corpus's 
			root directory.
        	@type copyright_file: C{string}
        	@param copyright_file: The path to a file containing a
            		copyright notice for the corpus.  If this is a relative
            		path, then it is interpreted relative to the corpus's 
			root directory.
        	@type default_tokenizer: 
			L{TokenizerI<nltk.tokenizer.TokenizerI>}
        	@param default_tokenizer: The default tokenizer that should be
            		used for the corpus reader's L{tokenize} method.
		"""
		# Compile regular expressions.
       		if isinstance(items_regexp, type('')):
       	     		items_regexp = re.compile(items_regexp)
        	if groups is None: groups = []
        	else: groups = groups[:]
        	for i in range(len(groups)):
            		if isinstance(groups[i][1], type('')):
                		groups[i] = (groups[i][0], 
					re.compile(groups[i][1]))

      		# Save parameters
        	self._name = name
   		self._original_rootdir = rootdir
       		self._items_regexp = items_regexp
		self._file_suffix = file_suffix
		self._lang_suffixes = lang_suffixes
   		self._grouplists = groups
	        self._description = description
	        self._description_file = description_file
	        self._license = None
        	self._license_file = license_file
        	self._copyright = None
        	self._copyright_file = copyright_file
        	self._default_tokenizer = default_tokenizer

        	# Postpone actual initialization until the corpus is 
		# accessed; this gives the user a chance to call 
		# set_basedir(), and prevents "import nltk.corpus" from 
		# raising an exception. We'll also want to re-initialize
		# the corpus if basedir ever changes.
        	self._basedir = None
        	self._rootdir = None
        	self._items = None
        	self._groups = None


	def _initialize(self):
        	"""
		Make sure that we're initialized.
		Initialization function, based on the nltk.corpus module's 
		SimpleCorpusReader, modified to be able to access parallel 
		corpus files.
		"""
        	# If we're already initialized, then do nothing.
        	if self._basedir == get_basedir(): return

        	# Make sure the corpus is installed.
        	basedir = get_basedir()
        	if not os.path.isdir(os.path.join(basedir, 
				self._original_rootdir)):
           		raise IOError('%s is not installed' % self._name)
        	self._basedir = basedir
        	self._rootdir = os.path.join(basedir, self._original_rootdir)

        	# Build a filelist for the corpus
        	filelist = self._find_files(self._rootdir)
        	filelist = [os.path.join(*(file.split('/')))
                    	for file in filelist]

        	# Find the parallel corpus files that are items
		# 1.Get a list of unique file prefixes
		file_prefixes = []
		for f in filelist:
			match = self._items_regexp.match(f)
			if match and file_prefixes.count(match.group()) == 0:
				file_prefixes.append(match.group())  

		# 2.Append the language suffixes onto the file prefixes
		lang_filenames = [] 
		for fp in file_prefixes:
			lang_filename = [fp + lang for lang 
					in self._lang_suffixes] 
			lang_filenames.append(lang_filename)

		#3. Append the file suffixes onto the filenames
		full_names  = []
		for lf in lang_filenames: 
			full_names.append([file + self._file_suffix 
					for file in lf])
		self._items = full_names 

        	# Find the files for each group.
        	self._groups = {}
        	for (groupname, regexp) in self._grouplists:
            		self._groups[groupname] = [f for f in filelist
                                       if regexp.match(f)]

        	# Read metadata from files
        	if self._description is None and self._description_file \
			is not None:
            		path = os.path.join(self._rootdir, 
				self._description_file)
            		self._description = open(path).read()
        	if self._license is None and self._license_file is not None:
            		path = os.path.join(self._rootdir, self._license_file)
            		self._license = open(path).read()
        	if self._copyright is None and self._copyright_file is not None:
            		path = os.path.join(self._rootdir, self._copyright_file)
            		self._copyright = open(path).read()


    	def _find_files(self, path, prefix=''):
        	filelist = []
        	for name in os.listdir(path):
            		filepath = os.path.join(path, name)
            		if os.path.isfile(filepath):
                		filelist.append('%s%s' % (prefix, name))
            		elif os.path.isdir(filepath):
                		filelist += self._find_files(filepath,
                                             '%s%s/' % (prefix, name))
        	return filelist


class ParallelCorpusReader2(SimpleCorpusReader):
	"""
	This module contains functions to access a parallel corpus, 
	which is composed of a number of corresponding files 
	(1 per language). These files have corresponding names, but are 
	located in different directories - 1 per language. 

	For example the filenames:
	'en/ep-98-10-10.al' and 'de/ep-98-10-10.al' correspond in the 
	europarl parallel corpus where 'en' is the English directory and 
	'de' is the German directory. 

	For further information see the documentation for SimpleCorpusReader.
	"""

	def __init__(self,
                 	# Basic Information
                 	name, rootdir, items_regexp, lang_dirs,
                 	# Grouping
                 	groups=None,
                 	# Meta-data
                 	description=None, description_file=None, 
                 	license_file=None,
                 	copyright_file=None,
                 	# Formatting meta-data
                	default_tokenizer=WSTokenizer()):
		"""
		Construct a new corpus parallel corpus reader. Based on the 
		constructor for SimpleCorpusReadrer in nltk corpus module, 
		modified to include a list of C{lang_dirs} (1 per 
		language).  A filename in the parallel corpus is given 
		by concatenating each C{lang_dir} with the C{item_regeexp} 
		with an appropriate separator.
		
		The parameters C{description}, C{description_file}, 
		C{license_file}, and C{copyright_file} specify optional 
		metadata. For the parallel corpus reader's description, you 
		should use C{description} or C{description_file}, but not both.

        	@group Basic Information: name, rootdir, items_regexp, 
			lang_suffixes, file_suffix
       		@group Grouping: groups
        	@group Meta-data: description, license, copyright,
            		description_file, license_file, copyright_file
        	@group Formatting Meta-data: default_tokenizer

	        @type name: C{string}
       		@param name: The name of the corpus.  This name is used for
            		printing the corpus reader, and for constructing
	    		locations.  It should usually be identical to the 
			name of the variable that holds the corpus reader.
        	@type rootdir: C{string}
        	@param rootdir: The path to the root directory for the
            		corpus.  If C{rootdir} is a relative path, then it is
            		interpreted relative to the C{nltk.corpus} base 
			directory (as returned by L{nltk.corpus.get_basedir()}).
        	@type items_regexp: C{regexp} or C{string}
        	@param items_regexp: A regular expression over paths that
            		defines the set of files that should be listed as
            		entities for the corpus.  The paths that this is tested
            		against are all relative to the corpus's root directory.
            		Use the forward-slash character (C{'/'} to delimit
            		subdirectories; C{SimpleCorpusReader} will 
			automatically convert this to the appropriate path 
			delimiter for the operating system.
		@type lang_dirs: C{List} of C{string}
		@param lang_dirs: A list of the direcotry names that 
			indicate the language of the file. e.g. the directory 
			'en' might contain all the English files  and the 
			directory 'de' all the German files. 
        	@type groups: C{list} of C{(string, regexp)} tuples
        	@param groups: A list specifying the groups for the corpus.
            		Each element in this list should be a pair
            		C{(M{groupname}, M{regexp})}, where C{M{groupname}} 
			is the name of a group; and C{M{regexp}} is a regular
			expression over paths that defines the set of files 
			that should be listed as entities for that group.  
			The paths that these regular expressions are tested 
			against are all relative to the corpus's root 
			directory.  Use the forward-slash character (C{'/'} to 
			delimit subdirectories; C{SimpleCorpusReader} will 
			automatically convert this to the appropriate path 
			delimiter for the operating system.
        	@type description: C{string}
        	@param description: A description of the corpus.
        	@type description_file: C{string}
		@param description_file: The path to a file containing a
            		description of the corpus.  If this is a relative path,
            		then it is interpreted relative to the corpus's root
            		directory.
        	@type license_file: C{string}
        	@param license_file: The path to a file containing licensing
            		information about the corpus.  If this is a relative
            		path, then it is interpreted relative to the corpus's 
			root directory.
        	@type copyright_file: C{string}
        	@param copyright_file: The path to a file containing a
            		copyright notice for the corpus.  If this is a relative
            		path, then it is interpreted relative to the corpus's 
			root directory.
        	@type default_tokenizer: 
			L{TokenizerI<nltk.tokenizer.TokenizerI>}
        	@param default_tokenizer: The default tokenizer that should be
            		used for the corpus reader's L{tokenize} method.
		"""
		# Compile regular expressions.
       		if isinstance(items_regexp, type('')):
       	     		items_regexp = re.compile(items_regexp)
        	if groups is None: groups = []
        	else: groups = groups[:]
        	for i in range(len(groups)):
            		if isinstance(groups[i][1], type('')):
                		groups[i] = (groups[i][0], 
					re.compile(groups[i][1]))

      		# Save parameters
        	self._name = name
   		self._original_rootdir = rootdir
       		self._items_regexp = items_regexp
		self._lang_dirs = lang_dirs
   		self._grouplists = groups
	        self._description = description
	        self._description_file = description_file
	        self._license = None
        	self._license_file = license_file
        	self._copyright = None
        	self._copyright_file = copyright_file
        	self._default_tokenizer = default_tokenizer

        	# Postpone actual initialization until the corpus is 
		# accessed; this gives the user a chance to call 
		# set_basedir(), and prevents "import nltk.corpus" from 
		# raising an exception. We'll also want to re-initialize
		# the corpus if basedir ever changes.
        	self._basedir = None
        	self._rootdir = None
        	self._items = None
        	self._groups = None


	def _initialize(self):
        	"""
		Make sure that we're initialized.
		Initialization function, based on the nltk.corpus module's 
		SimpleCorpusReader, modified to be able to access parallel 
		corpus files.
		"""
        	# If we're already initialized, then do nothing.
        	if self._basedir == get_basedir(): return

        	# Make sure the corpus is installed.
        	basedir = get_basedir()
        	if not os.path.isdir(os.path.join(basedir, 
				self._original_rootdir)):
           		raise IOError('%s is not installed' % self._name)
        	self._basedir = basedir
        	self._rootdir = os.path.join(basedir, self._original_rootdir)

		dir = self._rootdir + '/' + self._lang_dirs[0]
        	# Build a filelist for the corpus
        	filelist = self._find_files(dir)
        	filelists = [os.path.join(*(file.split('/')))
                    	for file in filelist]

        	# Find the parallel corpus files that are items
		# returing a list of lists of corresponding filenames
		filenames = []
		for f in filelist:
			match = self._items_regexp.match(f)
			if match:
				filenames.append([dir + '/' + f 
					for dir in self._lang_dirs])
		self._items = filenames 

        	# Find the files for each group.
        	self._groups = {}
        	for (groupname, regexp) in self._grouplists:
            		self._groups[groupname] = [f for f in filelist
                                       if regexp.match(f)]

        	# Read metadata from files
        	if self._description is None and self._description_file \
			is not None:
            		path = os.path.join(self._rootdir, 
				self._description_file)
            		self._description = open(path).read()
        	if self._license is None and self._license_file is not None:
            		path = os.path.join(self._rootdir, self._license_file)
            		self._license = open(path).read()
        	if self._copyright is None and self._copyright_file is not None:
            		path = os.path.join(self._rootdir, self._copyright_file)
            		self._copyright = open(path).read()


    	def _find_files(self, path, prefix=''):
        	filelist = []
        	for name in os.listdir(path):
            		filepath = os.path.join(path, name)
            		if os.path.isfile(filepath):
                		filelist.append('%s%s' % (prefix, name))
            		elif os.path.isdir(filepath):
                		filelist += self._find_files(filepath,
                                             '%s%s/' % (prefix, name))
        	return filelist


###########################################################################
### De News Corpus

de_news = ParallelCorpusReader1("de_news_corpus", de_news_path,
	 r'de-news-\d\d\d\d-\d\d-\d\d', [".en", ".de"], ".al",
	 description_file ='../README')

###########################################################################
### Europarl Corpus

europarl = ParallelCorpusReader2("europarl_corpus", europarl_path,
	 r'ep-\d\d-\d\d-\d\d.al', ['en', 'de'])

##########################################################################

