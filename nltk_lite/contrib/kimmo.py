# Natural Language Toolkit: Kimmo Morphological Analyzer
#
# Copyright (C) 2001-2006 MIT
# Author: Carl de Marcken <carl@demarcken.org>
#         Beracah Yankama <beracah@mit.edu>
#         Robert Berwick <berwick@ai.mit.edu>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Kimmo Morphological Analyzer.  Supports proper recognizer completion,
generator ordering, kimmo control class, loader for own file format,
also .rul compatible with old pckimmo.
"""

# TODO: remove Unix dependencies

import Tkinter
import os, re, sys, types, string, glob, time, md5

from nltk_lite.contrib.fsa import *
from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize

############################# KIMMO GUI ##################################
"""
A gui for input of generative & recognition models
need 3 input boxes, one for text input, lexicon box, rules box
one output box?

need alternations rules and lexicon
plus 1 input test & recognition box.

we want to "step" through alternations
we want to "show" the rules that fire.
and we want batch mode, big file, or big input test with output.
"""
###########################################################################
from ScrolledText import ScrolledText

class KimmoGUI:
    def __init__(self, grammar, text, title='Kimmo Interface v1.78'):
        self.root = None
        try:
            self.dbgTracing = None
            self.highlightIds = []
            self.tagId = 0

            self.lexmd5 = None
            self.rulemd5 = None
            self.lexicalGraphWindow = None

            self.rulfilename = ''	
            self.lexfilename = ''
            self.altfilename = ''
            self.kimmoResultFile = ''

            self.helpFilename = 'kimmo.help'

            self._root = Tkinter.Tk()
            self._root.title(title)

            ctlbuttons = Tkinter.Frame(self._root)
            ctlbuttons.pack(side='top', fill='x')
            level1 = Tkinter.Frame(self._root)
            level1.pack(side='top', fill='none')
            Tkinter.Frame(self._root).pack(side='top', fill='none')
            level2 = Tkinter.Frame(self._root)
            level2.pack(side='top', fill='x')
            buttons = Tkinter.Frame(self._root)
            buttons.pack(side='top', fill='none')
            batchFrame = Tkinter.Frame(self._root)
            batchFrame.pack(side='top', fill='x')

            self.batchpath = Tkinter.StringVar()
            Tkinter.Label(batchFrame, text="Batch File:").pack(side='left')
            Tkinter.Entry(batchFrame, background='white', foreground='black',
                          width=30, textvariable=self.batchpath).pack(side='left')
            Tkinter.Button(batchFrame, text='Go!',
                           background='#a0c0c0', foreground='black',
                           command=self.batch).pack(side='left')

            self.debugWin = Tkinter.StringVar()	# change to a window and field eventually.
            Tkinter.Entry(batchFrame, background='grey', foreground='red',
                          width=30, textvariable=self.debugWin).pack(side='right')

            self.wordIn = Tkinter.StringVar()
            Tkinter.Label(level2, text="Generate or Recognize:").pack(side='left')
            Tkinter.Entry(level2, background='white', foreground='black',
                          width=30, textvariable=self.wordIn).pack(side='left')

            lexiconFrame = Tkinter.Frame(level1)
            Tkinter.Label(lexiconFrame, text="Lexicon & Alternations").pack(side='top',
                                                              fill='x')
            self.lexicon = ScrolledText(lexiconFrame, background='white',
                                              foreground='black', width=50, height=36, wrap='none')

            # setup the scrollbar
            scroll = Tkinter.Scrollbar(lexiconFrame, orient='horizontal',command=self.lexicon.xview)

            scroll.pack(side='bottom', fill='x')
            self.lexicon.configure(xscrollcommand = scroll.set)

            self.lexicon.pack(side='top')


            midFrame = Tkinter.Frame(level1)
            rulesFrame = Tkinter.Frame(midFrame)
            rulesFrame.pack(side='top', fill='x')
            Tkinter.Label(rulesFrame, text="Rules/Subsets").pack(side='top',
                                                              fill='x')
            self.rules = ScrolledText(rulesFrame, background='white',
                                              foreground='black', width=60, height=19, wrap='none')
            # setup the scrollbar
            scroll = Tkinter.Scrollbar(rulesFrame, orient='horizontal',command=self.rules.xview)
            scroll.pack(side='bottom', fill='x')
            self.rules.configure(xscrollcommand = scroll.set)

            self.rules.pack(side='top')

            midbetweenFrame = Tkinter.Frame(midFrame)
            midbetweenFrame.pack(side='top', fill='x')

            Tkinter.Button(midbetweenFrame, text='clear',
                           background='#f0f0f0', foreground='black',
                           command= lambda start=1.0, end=Tkinter.END : self.results.delete(start,end)
                           ).pack(side='right')

            Tkinter.Label(midbetweenFrame,
                          text="Results           ").pack(side='right')

            self.results = ScrolledText(midFrame, background='white',
                                              foreground='black', width=60, height=13, wrap='none')

            # setup the scrollbar
            scroll = Tkinter.Scrollbar(midFrame, orient='horizontal',command=self.results.xview)
            scroll.pack(side='bottom', fill='x')
            self.results.configure(xscrollcommand = scroll.set)

            self.results.pack(side='bottom')



            """
            alternationFrame = Tkinter.Frame(level1)
            Tkinter.Label(alternationFrame, text="Alternations").pack(side='top',
                                                              fill='x')
            self.alternation = ScrolledText(alternationFrame, background='white',
                                              foreground='black', width=1, wrap='none')
            self.alternation.pack(side='top')
            """

            Tkinter.Button(ctlbuttons, text='Quit',
                           background='#a0c0c0', foreground='black',
                           command=self.destroy).pack(side='left')

            self.loadMenuButton = Tkinter.Menubutton(ctlbuttons, text='Load', background='#a0c0c0', foreground='black', relief='raised')
            self.loadMenuButton.pack(side='left')
            self.loadMenu=Tkinter.Menu(self.loadMenuButton,tearoff=0)

            self.loadMenu.add_command(label='Load Lexicon', underline=0,command = lambda filetype='.lex', targetWindow = self.lexicon, tf = 'l' : self.loadTypetoTarget(filetype, targetWindow, tf))
            self.loadMenu.add_command(label='Load Rules', underline=0,command = lambda filetype='.rul', targetWindow = self.rules, tf = 'r' : self.loadTypetoTarget(filetype, targetWindow, tf))
            # self.loadMenu.add_command(label='Load Lexicon', underline=0,command = lambda filetype='.lex', targetWindow = self.lexicon : loadTypetoTarget(self, filetype, targetWindow))
            self.loadMenuButton["menu"]=self.loadMenu

#

            self.saveMenuButton = Tkinter.Menubutton(ctlbuttons, text='Save',background='#a0c0c0', foreground='black', relief='raised')
            self.saveMenuButton.pack(side='left')
            self.saveMenu=Tkinter.Menu(self.saveMenuButton,tearoff=0)
            self.saveMenu.add_command(label='Save Lexicon', underline=0,command = lambda filename=self.lexfilename, sourceWindow = self.lexicon : self.writeToFilefromWindow(filename, sourceWindow,'w',0,'l'))
            self.saveMenu.add_command(label='Save Rules', underline=0,command = lambda filename=self.rulfilename, sourceWindow = self.rules : self.writeToFilefromWindow(filename, sourceWindow,'w',0,'r'))
            self.saveMenu.add_command(label='Save Results', underline=0,command = lambda filename='.results', sourceWindow = self.results : self.writeToFilefromWindow(filename, sourceWindow,'w',0))
            self.saveMenu.add_command(label='Save All', underline=0,command = self.saveAll)
            self.saveMenuButton["menu"]=self.saveMenu


            Tkinter.Label(ctlbuttons, text="       Preset:").pack(side='left')

            self.configValue = Tkinter.StringVar()
            self.configsMenuButton = Tkinter.Menubutton(ctlbuttons, text='Configs', background='#a0c0c0', foreground='black', relief='raised')
            self.configsMenuButton.pack(side='left')
            self.configsMenu=Tkinter.Menu(self.configsMenuButton,tearoff=0)
            # read the directory for cfgs, add them to the menu
            # add path expander, to expand ~ & given home dirs.


            # !!! this does not handle student student directories, if not the current dir!
            currentconfigfiles = glob.glob('*.cfg')
            for x in currentconfigfiles:
            	newname = x # [0:len(x)-4]	# remove the '.cfg'
            	self.configsMenu.add_command(label=newname, underline=0,command = lambda newname=x : self.configLoader(newname)) # Callback(self.configLoader,newname))
            	# we want this to call load on the specific config file

            if len(currentconfigfiles) == 0:
            	# configsMenu.add_command(label='<none>',underline=0)
            	self.configsMenuButton.configure(text='<none>')
            	
            self.configsMenuButton["menu"]=self.configsMenu



			# toggle the different modes of this window
#            Tkinter.Button(ctlbuttons, text='->',
#                           background='#ffd564', foreground='red',
#                           command=self.generate).pack(side='right')
#
#            Tkinter.Checkbutton(ctlbuttons, text='Stepping',
#                           background='#b0f0d0', foreground='#008b45',
#                           command=self.generate).pack(side='right')

            self.tracingbtn = Tkinter.Button(ctlbuttons, text='Tracing',
                           background='#fff0f0', foreground='black',
                           command=lambda : self.create_destroyDebugTracing()).pack(side='right')


            self.graphMenuButton = Tkinter.Menubutton(ctlbuttons, text='Graph', background='#d0d0e8', foreground='black', relief='raised')
            self.graphMenuButton.pack(side='right')
            self.graphMenu=Tkinter.Menu(self.graphMenuButton,tearoff=0)

            self.graphMenu.add_command(label='Graph Lexicon', underline=0,command = lambda which = 'l' : self.graph(which))
            self.graphMenu.add_command(label='Graph FSA Rules', underline=0,command = lambda which = 'r' : self.graph(which))
            # self.loadMenu.add_command(label='Load Lexicon', underline=0,command = lambda filetype='.lex', targetWindow = self.lexicon : loadTypetoTarget(self, filetype, targetWindow))
            self.graphMenuButton["menu"]=self.graphMenu

            self.helpbtn = Tkinter.Button(ctlbuttons, text='Help',
                           background='#f0fff0', foreground='black',
                           command=self.kimmoHelp).pack(side='right')


            lexiconFrame.pack(side='left')
            midFrame.pack(side='left')
            # alternationFrame.pack(side='left')

            Tkinter.Button(level2, text='Generate',
                           background='#a0c0c0', foreground='black',
                           command=self.generate).pack(side='left')
            Tkinter.Button(level2, text='Recognize',
                           background='#a0c0c0', foreground='black',
                           command=self.recognize).pack(side='left')


			# setup the vars for kimmo
			# eventually make this a kimmo object
            """
            self.klexicons = []
            self.kalternations = []
            self.ksubsets = []
            self.kdefaults = []
            self.krules = []
            """

            self.kimmoinstance = None

            self.kimmoResultFile = ''
            self.traceWindow = ''

            self.debug = False

            self.configLoader('kimmo.cfg')
            # self.batchpath.set("kimmo.batch_test")

            # capture all print messages
            self.phOut = PrintHook()
            self.phOut.Start(self.capturePrint)


            # Enter mainloop.
            Tkinter.mainloop()
        except:
            print 'Error creating Tree View'
            self.destroy()
            raise

    def init_menubar(self):
        menubar = Tkinter.Menu(self._root)

        filemenu = Tkinter.Menu(menubar, tearoff=0)
        filemenu.add_command(label='Save Rules', underline=0,
                             command=self.save, accelerator='Ctrl-s')
        self._root.bind('<Control-s>', self.save)
        filemenu.add_command(label='Load Rules', underline=0,
                             command=self.load, accelerator='Ctrl-o')
        self._root.bind('<Control-o>', self.load)
        filemenu.add_command(label='Clear Rules', underline=0,
                             command=self.clear, accelerator='Ctrl-r')
        self._root.bind('<Control-r>', self.clear)
        filemenu.add_command(label='Exit', underline=1,
                             command=self.destroy, accelerator='Ctrl-q')
        self._root.bind('<Control-q>', self.destroy)
        menubar.add_cascade(label='File', underline=0,
                            menu=filemenu)
        self._root.config(menu=menubar)

    def guiError(self, *args):
    	self.debugWin.set(args[0].strip())
    	

    def create_destroyDebugTracing(self, *args):
    	# test creating tracing/debug window
    	
    	if (self.dbgTracing):
    		self.dbgTracing.destroy()
    		self.dbgTracing = None
    		self.debug = False

    	else:
	        try:
	            # have in its own special di decial class
	            self.dbgTracing = Tkinter.Toplevel()
	            self.dbgTracing.title("Tracing/Debug")
	            dbgTraceFrame2 = Tkinter.Frame(self.dbgTracing)
	            dbgTraceFrame2.pack(side='top', fill='x')
	            dbgTraceFrame = Tkinter.Frame(self.dbgTracing)
	            dbgTraceFrame.pack(side='top', fill='x',expand='yes')
	            self.traceWindow = ScrolledText(dbgTraceFrame, background='#f4f4f4',
	                                              foreground='#aa0000', width=45, height=24, wrap='none')
	
	            Tkinter.Button(dbgTraceFrame2, text='clear',
	                           background='#a0c0c0', foreground='black',
	                           command= lambda start=1.0, end=Tkinter.END : self.traceWindow.delete(start,end)
	                           ).pack(side='right')
	            Tkinter.Button(dbgTraceFrame2, text='Save',
	                           background='#a0c0c0', foreground='black',
	                           command= lambda file=self.kimmoResultFile,windowName=self.traceWindow,mode='w',auto=0 : self.writeToFilefromWindow(file,windowName,mode,auto)
	                           ).pack(side='left')
	
	
	            scroll = Tkinter.Scrollbar(dbgTraceFrame, orient='horizontal',command=self.traceWindow.xview)
	            scroll.pack(side='bottom', fill='x')
	
	            self.traceWindow.configure(xscrollcommand = scroll.set)
	            self.traceWindow.pack(side='bottom')
	
	
	            self.debug = True
	
	            # this will automatically clean itself up.
	            self.dbgTracing.protocol("WM_DELETE_WINDOW", self.create_destroyDebugTracing)
	
	        except:
	            print 'Error creating Tree View'
	            self.dbgTracing.destroy()
	            self.dbgTracing = None
	            self.debug = False
	            raise


    def writeToFilefromWindow(self, filename, windowName, mode, auto, wt=None):
    	# filename from var
    	
        # if not file: file='.txt'
    	# if append, add on, if overwrite, then ya

        if not (auto and windowName and filename):
        	
	        from tkFileDialog import asksaveasfilename
	        ftypes = [('Text file', '.txt'),('Rule file', '.rul'),('Lexicon file', '.lex'),('Alternations file', '.alt'),
	                  ('All files', '*')]
	        filename = asksaveasfilename(filetypes=ftypes,
	                                     defaultextension='', initialfile=filename)

        if not filename:
        	self.guiError('Need File Name')
        	return
        f = open(filename, 'w')
        f.write(windowName.get(1.0,Tkinter.END))
        f.close()

        if filename:
        	if wt == 'l': self.lexfilename = filename
        	elif wt == 'r': self.rulfilename = filename


    # create a window update class
    # and a window resize class

    # default save; all file names are known, so it saves to them.
    def saveAll(self, *args):
    	
    	# automatic write
    	self.writeToFilefromWindow(self.lexfilename,self.lexicon,'w',1)
    	self.writeToFilefromWindow(self.rulfilename,self.rules,'w',1)
    	# self.writeToFilefromWindow(self.altfilename,self.alternation,'w',1)
    	self.writeToFilefromWindow(self.resfilename,self.results,'w',1)
    	
    """
    def save(self, *args):
        "Save a rule/lexicon set to a text file"
        from tkFileDialog import asksaveasfilename
        ftypes = [('Text file', '.txt'),
                  ('All files', '*')]
        filename = asksaveasfilename(filetypes=ftypes,
                                     defaultextension='.txt')
        if not filename: return
        f = open(filename, 'w')
        f.write('---- Rules -----\n%s\n' % '\n'.join(self.getRules(False)))
        f.write('---- Lexicon -----\n%s\n' % '\n'.join(self.getLexicon(False)))
        f.close()
    """

    def configLoader(self,*args):
    	print args[0]
    	filename = args[0]

    	# if arg is a valid file, load by line.
    	# handle the different types of files
        if filename:
                f = read_kimmo_file(filename, self)
	        lines = f.readlines()
	        f.close()
	
		# clear all panes
	        self.clear()
		
		# now set the menu
	        self.configsMenuButton.configure(text=filename)
	
        	# reset gui name variables
        	# so that nothing gets overwritten.
        	# these file name variables will be changed if
        	# either the cfg changes it, or the person loads a different file
	
	        self.rulfilename = ''	
	        self.lexfilename = ''
	        self.altfilename = ''
	        self.kimmoResultFile = ''
	        self.batchpath.set('')
	
	        for line in lines:
	            line = line.strip()
	            cfgargs = line.split(":")
	            for x in range(len(cfgargs)): cfgargs[x] = cfgargs[x].strip()
	
	            if len(line) == 0: continue
	            elif (line[0] == '#') or (line[0] == ';'): continue	# comment
	            elif cfgargs[0] == 'lexicon':
	            	self.lexfilename = self.loadIntoWindow(os.path.expanduser(cfgargs[1]),self.lexicon)
	            elif cfgargs[0] == 'rules':
	            	self.rulfilename = self.loadIntoWindow(os.path.expanduser(cfgargs[1]),self.rules)
	            #elif cfgargs[0] == 'alternations':
	            #	self.loadIntoWindow(cfgargs[1],self.alternation)
	            #	self.altfilename = cfgargs[1]
	            elif cfgargs[0] == 'results':
	            	self.kimmoResultFile = os.path.expanduser(cfgargs[1])
	            	self.resfilename = os.path.expanduser(cfgargs[1])
	            elif cfgargs[0] == 'batch': self.batchpath.set(os.path.expanduser(cfgargs[1]))
	            # !
	            else: self.guiError('unknown line :' + line)
	            # print line
    	
    	else: self.guiError('Empty Filename')
    	
    	

    def loadIntoWindow(self, filename, windowField):
        "Load rule/lexicon set from a text file directly into the window pane specified"
        # filename = args[0]
        # windowField = args[1]

        if filename:
	        filename = os.path.expanduser(filename)
	        f = read_kimmo_file(filename, self)
	        lines = f.readlines()
	        f.close()

	        text = []
	        for line in lines:
	            line = line.strip()
	            text.append(line)

	        # empty the window now that the file was valid
	        windowField.delete(1.0, Tkinter.END)
	
	        windowField.insert(1.0, '\n'.join(text))
	
	        return filename
        return ''	

    	# opens a load dialog for files of a specified type to be loaded into a specified window
    def loadTypetoTarget(self, fileType, targetWindow, ftype = None):
    	
    	if not (fileType and targetWindow): return
    	
    	from tkFileDialog import askopenfilename
        ftypes = [(fileType, fileType)]

        filename = askopenfilename(filetypes=ftypes, defaultextension=fileType)

        self.loadIntoWindow(filename, targetWindow)

        # set the config menu to blank
        self.configsMenuButton.configure(text='<none>')

        # !!! remember to reset all the filenames as well!
        if filename:
        	if ftype == 'l': self.lexfilename = filename
        	elif ftype == 'r': self.rulfilename = filename

    def load(self, *args):
    	# graphical interface to file loading.
    	
        "Load rule/lexicon set from a text file"
        from tkFileDialog import askopenfilename
        ftypes = [('Text file', '.txt'),
                  ('All files', '*')]
        # filename = askopenfilename(filetypes=ftypes, defaultextension='.txt')
        filename = 'kimmo.lex'

        if filename:
	        f = read_kimmo_file(filename, self)
	        lines = f.readlines()
	        f.close()
	
	        rules = []
	        lexicon = []
	        alternations = []
	
	        state = 'rules'
	        for line in lines:
	            line = line.strip()
	            lexicon.append(line)
	
	        self.clear()
	        self.lexicon.insert(1.0, '\n'.join(lexicon))


        # now load up the alternations

        filename = 'kimmo.alt'

        if filename:
	        f = read_kimmo_file(filename, self)
	        lines = f.readlines()
	        f.close()
	
	        for line in lines:
	            line = line.strip()
	            alternations.append(line)

	        self.alternation.insert(1.0, '\n'.join(alternations))

        filename = 'kimmo.rul'

        if filename:
	        f = read_kimmo_file(filename, self)
	        lines = f.readlines()
	        f.close()
	
	        for line in lines:
	            line = line.strip()
	            rules.append(line)

	        self.rules.insert(1.0, '\n'.join(rules))

    def clear(self, *args):
        "Clears the grammar and lexical and sentence inputs"
        self.lexicon.delete(1.0, Tkinter.END)
        self.rules.delete(1.0, Tkinter.END)
        # self.alternation.delete(1.0, Tkinter.END)
        self.results.delete(1.0, Tkinter.END)

    def destroy(self, *args):
        if self._root is None: return
        self.phOut.Stop()
        self._root.destroy()
        self._root = None

# for single stepping through a trace.
# need to make the kimmo class capable of being interrupted & resumed.
    def step(self, *args):
    	print 'a'

    def singlestep(self, *args):
    	print 'a'

    def batch(self, *args):
    	filename = self.batchpath.get()
    	if filename:
    		f = read_kimmo_file(filename, self)
    		lines = f.readlines()
    		f.close()
	        	    		
    		self.initKimmo()
    		
    		# space the results out a little
    		self.results.insert(1.0, '\n')
    		
    		results_string = ''
    		for line in lines:
    							# a 'g word' 'r word' format
    			singleword = line.strip()	# should be a single word, no spaces, etc.
    			spcr = re.compile(r"\s+")
    			linevals = []
    			linevals = spcr.split(singleword)
    							
    			
    			batch_result = []
    			batch_result_str = ''
    			if not singleword: continue	# ignore blank lines
    			elif (singleword[0] == '#') or (singleword[0] == ';'): 	# commented;
    				results_string += (singleword + '\n')
    				# self.results.insert(Tkinter.END, singleword + '\n')			# send directly to results pane

    			elif (linevals[0] == 'g') and (len(linevals) == 2):
    				batch_result = self.kimmoinstance.generate(linevals[1])
    			elif (linevals[0] == 'r') and (len(linevals) == 2):
    				batch_result = self.kimmoinstance.recognize(linevals[1])
    				
    			elif '+' in singleword:
    				batch_result = self.kimmoinstance.generate(singleword)
    			else:
    				batch_result = self.kimmoinstance.recognize(singleword)
    			
    			# if a valid results
    			if len(batch_result) > 0:
    				for x in batch_result: batch_result_str = batch_result_str + x
    				batch_result_str = batch_result_str + '\n'
    				results_string += (batch_result_str)
    				# self.results.insert(Tkinter.END, batch_result_str)
    			
    		# place a separator between results
    		self.results.insert(1.0, '----- '+ time.strftime("%a, %d %b %Y %I:%M %p", time.gmtime()) +' -----\n')	
    		self.results.insert(2.0, results_string)	
    		self.results.see(1.0)
	
    		if self.traceWindow:
    			self.highlightMatches('    BLOCKED',self.traceWindow,'#ffe0e0')	
    			self.highlightMatches('      AT END OF WORD',self.traceWindow,'#e0ffe0')	
    			

    	# if the path is set, load the file
    		# init the engine
    		# choose between recognize & generate



	# generation test
    def generate(self, *args):
        if self._root is None: return

        if len(self.wordIn.get()) > 0:
	        self.initKimmo()
	
	        tmpword = self.wordIn.get()

	        tmpword.strip()
	
	        # generate_result = _generate_test(self.ks, tmpword)
	        generate_result = self.kimmoinstance.generate(tmpword)
	        generate_result_str = ''
	        # convert list to string
	        for x in generate_result: generate_result_str = generate_result_str + x
	        generate_result_str = generate_result_str + '\n'
	        self.results.insert(1.0, generate_result_str)
	
	        if self.dbgTracing:
    			self.highlightMatches('    BLOCKED',self.traceWindow,'#ffe0e0')	
    			self.highlightMatches('      AT END OF WORD',self.traceWindow,'#e0ffe0')	
    			self.highlightMatches('SUCCESS!',self.traceWindow,'#e0ffe0')

	
    def recognize(self, *args):
    	self.lexicon.tag_delete("highlight")
        if self._root is None: return

        if len(self.wordIn.get()) > 0:
	        self.initKimmo()
	
	        tmpword = self.wordIn.get()
	        # pad with terminators
	        tmpword.strip()
	
	        # recognize_result = _recognize_test(self.ks, tmpword, self.km)
	        recognize_result = self.kimmoinstance.recognize(tmpword)
	        recognize_result_str = ''
	        # convert list to string
	        for x in recognize_result: recognize_result_str = recognize_result_str + x
	        recognize_result_str = recognize_result_str + '\n'
	        self.results.insert(1.0, recognize_result_str)
	
	        if self.dbgTracing:
    			self.highlightMatches('    BLOCKED',self.traceWindow,'#ffe0e0')	
    			self.highlightMatches('      AT END OF WORD',self.traceWindow,'#e0ffe0')	



	# accept gui graph command
	# create kimmoinstance
	# and then process / display one of the graphs.
    def graph(self, which):
    	
    	self.initKimmo()
    	graphtitle = ''
    	
    	
    	# we want to save in the local dir.
    	# lex/rulefilenames are fully qualified.
    	
    	# so we test the local dir & strip the path off of the filename.
    	

    	# check & set path, if necessary, need read and write access to path
    	path = ''
    	pathstatus = os.stat('./')	# 0600 is r/w, binary evaluation
    	if not ((pathstatus[0] & 0600) == 0600):
    		path = '/tmp/' + str(os.environ.get("USER")) + '/' # need terminating /
    		if not os.path.exists(path):
    			os.mkdir(path,0777)
    	
    	pathre = re.compile(r"^.*\/")
    	
    	if which == 'l':
    		graphfname = path + pathre.sub("", self.lexfilename)
    		dotstring = dotformat(self.kimmoinstance.lexicalNodes)
    		leximagefile = dot2image(graphfname, dotstring)
    		graphtitle = 'Lexicon Graph'

    	elif which == 'r':
    		graphfname = path + pathre.sub("", self.rulfilename)
    		
    		tmpOptions = []
    		for x in self.kimmoinstance.fsasNodes:
    			# print x['name']
    			tmpOptions.append(x['name'])
    			
    		ld = ListDialog(self._root,tmpOptions,"Select FSA")
    		
    		if not ld.result: return
    		
    		# now create the dotstring & image from the (single) selection
    		dotstring = dotformat(self.kimmoinstance.fsasNodes[string.atoi(ld.result[0])]['nodes'])
    		graphtitle = 'FSA ' + self.kimmoinstance.fsasNodes[string.atoi(ld.result[0])]['name']
    		
    		# make file read:
    		# something.rul.1.gif  (where 1 is the rule index number)
    		graphfname += ('.' + str(ld.result[0]))
    		
    		# check if that file already exists, if so, append an iteration number onto it.
    		
    		leximagefile = dot2image(graphfname, dotstring)
    		

    	# if this is an imagefile, then create a new window for it.
    	if leximagefile:
	    	if self.lexicalGraphWindow: self.lexicalGraphWindow.destroy()
	    	self.lexicalGraphWindow = tkImageView(leximagefile, graphtitle)



    	# validates the lexicon against the alternations to make certain there
    	# are no misreferences/mispellings of refs.
    def validate(self,*args):
    	self.tagId = 1
    	
    	for x in self.lexicon.tag_names(): self.lexicon.tag_delete(x)
    	
    	# for x in self.highlightIds: x[0].tag_delete(x[1])
    	
    	for l in self.kimmoinstance.validateLexicon:
    		if not l in self.kimmoinstance.validateAlternations:
    			if l:
    				self.guiError('Unused Alternation')
    				self.highlightMatches(l,self.lexicon,'#ffffc0')
    	
    	for a in self.kimmoinstance.validateAlternations:
    		if not a in self.kimmoinstance.validateLexicon:
    			if a:
    				self.guiError('Unknown Alternation Name')
    				self.highlightMatches(a,self.lexicon,'#ffffc0')
    	

    # highlight matching words in given window
    def highlightMatches(self, word, window,color):
    	# assumes unbroken with whitespace words.
    	if not word: return
    	
    	matchIdx = '1.0'
    	matchRight = '1.0'
    	while matchIdx != '':
    		matchIdx = window.search(word,matchRight,count=1,stopindex=Tkinter.END)
    		if matchIdx == '': break
    		
    		strptr = matchIdx.split(".")
    		matchRight = strptr[0] + '.' + str((int(strptr[1],10) + len(word)))

    		window.tag_add(self.tagId, matchIdx, matchRight )
    		window.tag_configure(self.tagId,background=color, foreground='black')
    		self.highlightIds.append([window,self.tagId])
    		self.tagId = self.tagId + 1
    	
    	

# INIT KIMMO
    def initKimmo(self, *args):
		"""
		Initialize the Kimmo engine from the lexicon.  This will get called no matter generate
		or recognize.  (i.e. loading all rules, lexicon, and alternations
		"""
	        # only initialize Kimmo if the contents of the *rules* have changed
		tmprmd5 = md5.new(self.rules.get(1.0, Tkinter.END))
		tmplmd5 = md5.new(self.lexicon.get(1.0, Tkinter.END))
		if (not self.kimmoinstance) or (self.rulemd5 != tmprmd5) or (self.lexmd5 != tmplmd5):
			self.guiError("Creating new Kimmo instance")
			self.kimmoinstance = KimmoControl(self.lexicon.get(1.0, Tkinter.END),self.rules.get(1.0, Tkinter.END),'','',self.debug)
			self.guiError("")
			self.rulemd5 = tmprmd5
			self.lexmd5 = tmplmd5

		if not self.kimmoinstance.ok:
			self.guiError("Creation of Kimmo Instance Failed")
			return
		if not self.kimmoinstance.m.initial_state() :
			self.guiError("Morphology Setup Failed")
		elif self.kimmoinstance.errors:
			self.guiError(self.kimmoinstance.errors)
			self.kimmoinstance.errors = ''
		# self.validate()

    def refresh(self, *args):
        if self._root is None: return
        print self.wordIn.get()


# CAPTURE PYTHON-KIMMO OUTPUT
# redirect to debug window, if operational
    def capturePrint(self,*args):
    	# self.debugWin.set(string.join(args," "))
    	
    	# if there is a trace/debug window
    	if self.dbgTracing:
    		self.traceWindow.insert(Tkinter.END, string.join(args," "))
    		self.traceWindow.see(Tkinter.END)
    		
    	
    	# otherwise, just drop the output.
    	
    	# no no, if tracing is on, but no window, turn tracing off and cleanup window
    	
    	# !!! if tracing is on, but window is not defined, create it.
    		# this will cause a post-recover from an improper close of the debug window
    		
    	# if tracing is not on, ignore it.
    	
    	# return 1,1,'Out Hooked:'+text
    	return 0,0,''
    	
    	

    def kimmoHelp(self,*args):

    	# helpText = """
    	# """
    	    	
    	# load help into helpfile

    	# helpText = Tkinter.StringVar()
    	helpText = ''
    	try: f = open(self.helpFilename, 'r')
    	except IOError, e:
    		self.guiError("HelpFile not loaded")
    		return
    		
    	self.guiError("")	# no errors to report here
    				# this is not the best idea, what if there are many errors
    				# from different functions?

    	helpText = str(f.read())
    	f.close()    	
    	
    	# clean any crl stuff
    	helpText = re.sub("\r","",helpText)

    	
    	helpWindow = Tkinter.Toplevel()
    	helpWindow.title("PyKimmo Documentation & Help")
    	
    	# help = Tkinter.Label(helpWindow,textvariable=helpText, justify='left' ) #
    	help = ScrolledText(helpWindow, background='#f0f0f0',
                            foreground='black', width=70, height=40,wrap='none',
                            font='Times 12 bold') #

        help.pack(side='top')
        help.insert(1.0, helpText)
    	# setup the scrollbar
    	scroll = Tkinter.Scrollbar(helpWindow, orient='horizontal',command=help.xview)
    	scroll.pack(side='bottom', fill='x')
    	help.configure(xscrollcommand = scroll.set)

    	# now highlight up the file
    	matchIdx = Tkinter.END
    	matchRight = Tkinter.END
    	matchLen = Tkinter.IntVar()
    	tagId = 1
    	while 1:
    		matchIdx = help.search(r"::[^\n]*::",matchIdx, stopindex=1.0, backwards=True, regexp=True, count=matchLen  )
    		if not matchIdx: break
    		
    		matchIdxFields = matchIdx.split(".")
    		matchLenStr = matchIdxFields[0] + "." + str(string.atoi(matchIdxFields[1],10) + matchLen.get())

    		print (matchIdx, matchLenStr)
    		help.tag_add(tagId, matchIdx, matchLenStr )
    		help.tag_configure(tagId, background='aquamarine', foreground='blue', underline=True)
    		tagId += 1
    		

    	

################################ PRINT HOOK ######################
# this class gets all output directed to stdout(e.g by print statements)
# and stderr and redirects it to a user defined function
class PrintHook:
    #out = 1 means stdout will be hooked
    #out = 0 means stderr will be hooked
    def __init__(self,out=1):
        self.func = None ##self.func is userdefined function
        self.origOut = None
        self.out = out
    #user defined hook must return three variables
    #proceed,lineNoMode,newText
    def TestHook(self,text):
        f = open('hook_log.txt','a')
        f.write(text)
        f.close()
        return 0,0,text
    def Start(self,func=None):
    	if self.out:
            sys.stdout = self
            self.origOut = sys.__stdout__
        else:
       	    sys.stderr= self
            self.origOut = sys.__stderr__
        if func:
            self.func = func
        else:
            self.func = self.TestHook
    #Stop will stop routing of print statements thru this class
    def Stop(self):
    	self.origOut.flush()
    	if self.out:
            sys.stdout = sys.__stdout__
        else:
            sys.stderr = sys.__stderr__
            self.func = None
    #override write of stdout
    def write(self,text):
        proceed = 1
        lineNo = 0
        addText = ''
        if self.func != None:
            proceed,lineNo,newText = self.func(text)
            if proceed:
            	if text.split() == []:
            		self.origOut.write(text)
            	else:
                #if goint to stdout then only add line no file etc
                #for stderr it is already there
                    if self.out:
                    	if lineNo:
                            try:
               			raise "Dummy"
               	            except:
               			newText =  'line('+str(sys.exc_info()[2].tb_frame.f_back.f_lineno)+'):'+newText
               			codeObject = sys.exc_info()[2].tb_frame.f_back.f_code
              			fileName = codeObject.co_filename
              			funcName = codeObject.co_name
                    	self.origOut.write('file '+fileName+','+'func '+funcName+':')
                	self.origOut.write(newText)
    #pass all other methods to __stdout__ so that we don't have to override them
    def __getattr__(self, name):
    	return self.origOut.__getattr__(name)

class tkImageView:
	def __init__(self, imagefileName, title):
		self._root = Tkinter.Toplevel()
		self._root.title(title + ' (' + imagefileName + ')')
		self.image = Tkinter.PhotoImage("LGraph",file=imagefileName)

		Tkinter.Label(self._root, image=self.image).pack(side='top',fill='x')
		# self._root.mainloop()
		
	def destroy(self, *args):
		if self._root:
			self._root.destroy()
		self._root = None
		self.image = None
		
	
######################### Dialog Boxes ##############################
class ListDialog(Tkinter.Toplevel):

    def __init__(self, parent, listOptions, title = None):

        Tkinter.Toplevel.__init__(self, parent)
        self.transient(parent)

        if title:
            self.title(title)

        self.parent = parent

        self.result = None

        body = Tkinter.Frame(self)

        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)

        box = Tkinter.Frame(self)
        Tkinter.Label(box,text="Select an FSA to graph").pack(side='top',fill='x')
        box.pack()



        self.listbox(listOptions)

        self.buttonbox()

        self.grab_set()

        if not self.initial_focus:
            self.initial_focus = self

        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
                                  parent.winfo_rooty()+50))

        self.initial_focus.focus_set()

        self.wait_window(self)

    #
    # construction hooks

    def body(self, master):
        # create dialog body.  return widget that should have
        # initial focus.  this method should be overridden

        pass


    def listbox(self, listOptions):
    	box = Tkinter.Frame(self)
    	self.lb = Tkinter.Listbox(box,height=len(listOptions),width=30,background='#f0f0ff', selectbackground='#c0e0ff'
    		,selectmode='single')
    	self.lb.pack()
    	
    	for x in listOptions:
    		self.lb.insert(Tkinter.END,x)
    	
    	box.pack()

    def buttonbox(self):
        # add standard button box. override if you don't want the
        # standard buttons

        box = Tkinter.Frame(self)

        w = Tkinter.Button(box, text="OK", width=10, command=self.ok, default="active")
        w.pack(side="left", padx=5, pady=5)
        w = Tkinter.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side="left", padx=5, pady=5)

        self.bind("&lt;Return&gt;", self.ok)
        self.bind("&lt;Escape&gt;", self.cancel)

        box.pack()

    #
    # standard button semantics

    def ok(self, event=None):

        if not self.validate():
            self.initial_focus.focus_set() # put focus back
            return

        self.withdraw()
        self.update_idletasks()

        self.apply()

        # we want to return self.lb.curselection()
        self.result = self.lb.curselection()

        self.cancel()


    def cancel(self, event=None):

        # put focus back to the parent window
        self.parent.focus_set()
        self.destroy()

    #
    # command hooks

    def validate(self):

        return 1 # override

    def apply(self):

        pass # override





################################ Dot Grapher ######################
# given a state table with names, draw graphs in dot format.

"""
     +  CNsib  +    s    #    y    o   @
     e  CNsib  @    s    #    i    o   @
 1:  0    2    1    2    1    2    7   1
 2:  3    2    5    2    1    2    7   1
 3.  0    0    0    4    0    0    0   0
 4.  0    0    1    0    1    0    0   0
 5:  0    1    1    6    1    1    1   1
 6:  0    1    0    1    0    1    1   1
 7:  3    2    1    2    1    2    7   1
"""

# so first we will create the states.
# then we will write the edges & name them.
# name 0 as fail

# call the dot drawer on the file & display the graph.

def dotformat(nodeEdgeAry):
	# choose graphsize based upon number of nodes
	graphWH = '4,4'
	if len(nodeEdgeAry) > 3: graphWH = '5,5'
	if len(nodeEdgeAry) > 5: graphWH = '6,6'
	if len(nodeEdgeAry) > 7: graphWH = '7,7'
	if len(nodeEdgeAry) > 10: graphWH = '7.5,7.5'
	
	# print len(nodeEdgeAry)
	# print graphWH
	
	dotstring = ''
	dotstring += "	size=\""+ graphWH +"\"\n"
	# dotstring += "	page=\"7,7\"\n"
	dotstring += "	ratio=fill\n"
	# dotstring += "	rankdir=LR\n"
	# dotstring += "	center=1\n"
	for x in nodeEdgeAry:
		if x['node'] == 'Begin': features = ' [' + 'shape=box,color=lightblue,style=filled] '
		elif x['node'] == 'End': features = ' [' + 'color="Light Coral",style=filled] '
		elif x['features'] : features = ' [' + x['features'] + '] '
		elif not x['features'] : features = ''
		
		dotstring += ('	"' + x['node'] + '" ' + features + ";\n")
		for e in range(len(x['edges'])):
			dotstring += ('	"' + x['node'] + '" -> "' + x['edges'][e] + '" ')
			if e < len(x['edgenames']) : dotstring += ('[label="\l'+ x['edgenames'][e] + '"]' )
			dotstring += ";\n"
			
	dotstring = "digraph autograph {\n" + dotstring + "\n}\n"
	return dotstring
		
def _classeq(instance1, instance2):
    """
    @return: true iff the given objects are instances of the same
        class.
    @rtype: C{bool}
    """
    return (type(instance1) == types.InstanceType and
            type(instance2) == types.InstanceType and
            instance1.__class__ == instance2.__class__)

# given a dot string, write to a tmp file and invoke the grapher
# return a filename to open.
# imagetype is hardcoded for now
def dot2image(filename, dotstring):
	dotfilename = filename + '.dot'
	# imgfilename = filename + '.gif'
	psfilename = filename + '.ps'
	imgfilename = filename + '.ppm'
	pngfilename = filename + '.png'

	# whack the file if already there... (for now)
	f = open(dotfilename, 'w')
	f.write(dotstring)
	f.close()

	os.system('dot -Tps -o ' + psfilename +' ' + dotfilename)	
	# os.system('dot -Tgif -o ' + imgfilename +' ' + dotfilename)

	#print filename + "\n"
	#print imgfilename + "\n"

	# cheap hack now that graphviz is not working right...
	os.system('rm -f ' + imgfilename)
	os.system('pstopnm -stdout -portrait -ppm ' + psfilename + ' > ' + imgfilename)

	if os.path.isfile(imgfilename) : return imgfilename
	
	return ''





################################ KIMMO SET ######################
		
# ----------- KIMMOCONTROL ---------------
# Master instance for creating a kimmo object
# from files or strings or rules & lexical entries
# -------------------------------------
class KimmoControl:
    def __init__(self, lexicon_string, rule_string, lexicon_file, rule_file, debug):

    	self.validateLexicon = []
    	self.validateAlternations = []
    	
    	self.lexicalNodes = []	# transition states and edges for graphing lexicon
    	self.ruleNodes = []	# transition states & edges for graphing of rules
    	
    	# a better way is just to use a destructor and check if the object exists.
    	self.ok = 0
    	self.errors = ''
    	
    	# load lexicon file
    	if lexicon_file:
		f = read_kimmo_file(lexicon_file)
	        lexicon_string = string.join(f.readlines(),"")
	        f.close()

    	# load rule file
    	if rule_file:
		f = read_kimmo_file(rule_file)
	        rule_string = string.join(f.readlines(),"")
	        f.close()    	
    	
    	try:
    		self.processRules(rule_string)
    		self.processLexicon(lexicon_string)
    		self.m = KimmoMorphology(self.kalternations, self.klexicons)
    		self.m.set_boundary(self.boundary_char)
    		self.s = KimmoRuleSet(self.ksubsets, self.kdefaults, self.krules)
    		self.s.debug = debug
    		self.ok = 1
    	except RuntimeError, e:
    		self.errors = ('Caught:' + str(e) + ' ' + self.errors)
    		print 'Caught:', e
    		print "Setup of the kimmoinstance failed.  Most likely cause"
    		print "is infinite recursion due to self-referential lexicon"
    		print "For instance:"
    		print "Begin: Begin Noun End"
    		print "Begin is pointing to itself.  Simple example, but check"
    		print "to insure no directed loops"
    		self.ok = 0
    	
    	

    def generate(self, word):
    	if self.boundary_char: word += self.boundary_char
    	genlist = _generate_test(self.s, word)
    	
    	genliststr = genlist.__repr__()
    	if self.boundary_char: genliststr = genliststr.replace(self.boundary_char,'')

    	return eval(genliststr)
    	
    def recognize(self, word):
    	return _recognize_test(self.s, word, self.m)


	# run a batch and print to console.  This is different than the
	# batch for the gui;
	# the kimmo object should already be created when the batch is run.
	# the output is also not formatted nicely
    def batch(self, filename):
    	if filename:
    		f = read_kimmo_file(filename)
    		lines = f.readlines()
    		f.close()
    		
    		# space the results out a little
    		results_string = ''
    		for line in lines:
    							# a 'g word' 'r word' format
    			singleword = line.strip()	# should be a single word, no spaces, etc.
    			spcr = re.compile(r"\s+")
    			linevals = []
    			linevals = spcr.split(singleword)
    			
    			batch_result = []
    			batch_result_str = ''
    			if not singleword: continue	# ignore blank lines
    			elif (singleword[0] == '#') or (singleword[0] == ';'): 	# commented;
    				results_string += (singleword + '\n')

    			elif (linevals[0] == 'g') and (len(linevals) == 2):
    				batch_result = self.generate(linevals[1])
    			elif (linevals[0] == 'r') and (len(linevals) == 2):
    				batch_result = self.recognize(linevals[1])
    				
    			elif '+' in singleword:
    				batch_result = self.generate(singleword)
    			else:
    				batch_result = self.recognize(singleword)
    			
    			# if a valid results
    			if len(batch_result) > 0:
    				for x in batch_result: batch_result_str = batch_result_str + x
    				batch_result_str = batch_result_str + '\n'
    				results_string += (batch_result_str)
    			
    		# place a separator between results
    		print '----- '+ time.strftime("%a, %d %b %Y %I:%M %p", time.gmtime()) +' -----\n'
    		print results_string




	# move this out into a kimmo files & frontend class.
	# make this also process alternations, if contained.
    def processLexicon(self, text):
        """
        Takes the currently typed in lexicon and turns them from text into
        the kimmo lexicon array.
        """
        # text = self.lexicon.get(1.0, Tkinter.END)
        testlex = []
        self.klexicons = []	# lexicons needs to be an object of the gui scope
        lexigroup = ''
        kimmoWords = []
        alternationText = ''

        tmpnode = {}		# a node and its edges
        tmpnode['node'] = ''
        tmpnode['features'] = ''
        tmpnode['edges'] = []
        tmpnode['edgenames'] = []
        self.lexicalNodes = []	# list of nodes & their edges for the lexicon

        for item in text.split("\n"):
       	    # ''   None   	Genitive
            cleanLine = item.strip()


            if len(cleanLine) == 0 : continue		# blank line
            elif cleanLine[0] == '#' : continue		# a comment
            elif cleanLine[0] == ';' : continue		# a comment

            # elsif there is a : then start up this lexicon entry.
            # if there is already a value in lexigroup, then append to lexicons
            # assume that : is the last char.
            # LEXICON N_ROOT1
            elif cleanLine[len(cleanLine)-1] == ':' :
            	if (len(lexigroup) > 0):
            		if len(kimmoWords):
            			# print lexigroup
            			# print kimmoWord
            			self.klexicons.append( KimmoLexicon(lexigroup, kimmoWords) )
            			self.lexicalNodes.append(tmpnode)
            		kimmoWords = []
            	lexigroup = cleanLine[0:len(cleanLine)-1]	# remove trailing ':'  , new group
            	
            	# create the state transitions for the lexicon.
            	tmpnode = {}
            	tmpnode['node'] = lexigroup
            	tmpnode['features'] = ''
            	tmpnode['edges'] = []
            	tmpnode['edgenames'] = []
            	
            	self.validateLexicon.append(lexigroup)
            	# print lexigroup
            	
            # assume that a : contained in the line that is not a last char means it is an alternation.
            elif ':' in cleanLine:
            	alternationText += ( cleanLine + "\n")

            elif lexigroup:
            	p = re.compile(r"\s+")
            	moreitems = []
            	# moreitems = item.split(" ")			# make sure to add tabs and other whitespace..
            	moreitems = p.split(item)
            	
            	# this is splitting on the wrong char
            	
            	# *recollect*.  doesn't work on multiple spaces.
            	# this code only works for the last field
            	rangestart = -1
            	for x in range(len(moreitems)):
            		# print moreitems[x]
            		if (moreitems[x][0] == '"') and (rangestart < 0): rangestart = x
            		elif (moreitems[x][len(moreitems[x])-1] == '"') and (rangestart > -1):
            			rangeend = x
            			moreitems[rangestart] = string.join(moreitems[rangestart:rangeend+1], " ")

            	i = 0
            	for furtheritem in moreitems:
                	furtheritem = furtheritem.strip()
                	moreitems[i] = furtheritem
                	
                	if not len(moreitems[i]): continue
                	if i > 2 : continue
                	else: testlex.append(moreitems[i])
                	i += 1

            	for x in range(len(moreitems)):
            		if x > 2: continue
            		elif (moreitems[x] == '\'\'') or (moreitems[x] == '""'):
            			moreitems[x] = ''
            		elif (moreitems[x][0] == '"') and (moreitems[x][len(moreitems[x])-1] == '"'):
            			moreitems[x] = moreitems[x][1:len(moreitems[x])-1]
            		elif (moreitems[x][0] == '\'') and (moreitems[x][len(moreitems[x])-1] == '\''):
            			
            			tmpitem = moreitems[x]
            			moreitems[x] = tmpitem[1:(len(tmpitem)-1)]
            			
            		elif moreitems[x] == 'None' : moreitems[x] = None
            	
            	# EXPECTED FORMAT IS:
            	# WORD ALTERNATION DESCRIPTION
            	if len(moreitems) > 2 :
            		kimmoWords.append( KimmoWord(moreitems[0], moreitems[2], moreitems[1]) )
            		self.validateLexicon.append(moreitems[1])
            		# print moreitems
            	elif len(moreitems) > 1 :
            		kimmoWords.append( KimmoWord(moreitems[0], '', moreitems[1]) )
            		self.validateLexicon.append(moreitems[1])
            		
            	if (len(moreitems) > 1) and not (moreitems[1] in tmpnode['edges']):
            		tmpnode['edges'].append(moreitems[1])

            else :
            	# an undefined line.
            	self.errors += "Unknown Line in Lexicon (" + cleanLine + ")"

        # if the end of file and there is a group defined, add this last group
        if (len(lexigroup) > 0) and (len(kimmoWords)):
        	self.klexicons.append( KimmoLexicon(lexigroup, kimmoWords) )
        	self.lexicalNodes.append(tmpnode)

        # process the alternations
        # print alternationText
        self.processAlternations(alternationText)


        # return an array of state and edge objects.
        return self.lexicalNodes



    # process ALTERNATIONS
    # self.kalternations = [
	#	    KimmoAlternation('Begin',          [ 'N_ROOT', 'ADJ_PREFIX', 'V_PREFIX', 'End' ]),

    def processAlternations(self, text):
        """
        Takes the currently typed in alternations and turns them from text into
        the kimmo alternation array.
        """
        # text = self.alternation.get(1.0, Tkinter.END)
        testalt = []
        self.kalternations = []	# lexicons needs to be an object of the gui scope
        altgroup = ''
        kimmoAlts = []

        for line in text.split("\n"):
       	    # ''   None   	Genitive
            cleanLine = line.strip()

            if len(cleanLine) == 0 : continue		# blank line
            elif cleanLine[0] == '#' : continue		# a comment
            elif cleanLine[0] == ';' : continue		# a comment
            else:
            	# lets do this one differently.
            	# lets break it first, then keep on looping until we find the next group (signified by a : )
            	p = re.compile(r"\s+")
            	items = []
            	items = p.split(cleanLine)

            	for item in items:
	            	item_tmp = item.strip()
	            	
	            	
            		if len(item_tmp) == 0 : continue
            		# ALTERNATION V_root	
            		elif ':' in item_tmp :
            			# all all prior alternations to prior altgroup (if defined)
            			if len(altgroup) > 0:
            				if len(kimmoAlts) > 0:
	            				self.kalternations.append(
	            					KimmoAlternation(altgroup, kimmoAlts) )
	            					
	            				self.validateAlternations.append(altgroup)
	            				for x in kimmoAlts: self.validateAlternations.append(x)
	            				self.lexicalNodes.append(tmpnode)
            				
            				
            			# set new altgroup
            			altgroup = cleanLine[0:len(item_tmp)-1]
            			kimmoAlts = []
            			
            			tmpnode = {}
            			tmpnode['node'] = altgroup
            			tmpnode['features'] = 'color=\"aquamarine2\", style=filled'
            			tmpnode['edges'] = []
            			tmpnode['edgenames'] = []

            		
            		else :
            			# remove '' surrounding alternations
            			if (item_tmp[0] == '\'') and (item_tmp[len(item_tmp)-1] == '\''):
            				item_tmp = item_tmp[1:(len(item_tmp)-1)]
            			# convert None
            			elif item_tmp == 'None' : item_tmp = None
            				
            			# print 'a \'' + item_tmp + '\''
            			kimmoAlts.append(item_tmp)
            			
            			# add alternation edges ; order independent.
            			tmpnode['edges'].append(item_tmp)

        if len(altgroup) > 0:
        	if len(kimmoAlts) > 0:
	        	self.kalternations.append(
	            	KimmoAlternation(altgroup, kimmoAlts) )
	        	self.validateAlternations.append(altgroup)
	        	for x in kimmoAlts: self.validateAlternations.append(x)
	        	self.lexicalNodes.append(tmpnode)

        # print self.validateAlternations



    # RULES
    # Rule format
    # KimmoFSARule('08:elision: e:0 <= VCC*___+:0 V',
	#	                 '             Cpal C    e:0 e:@ +:0 Vbk V   @', # english.rul needed pairs re-ordered
	#	                 [ (1, True, [ 1,   1,   1,  2,  1,  2,  2,  1 ]),
	#	                   (2, True, [ 3,   6,   1,  2,  1,  2,  2,  1 ]),    # V...
	#	                   (3, True, [ 3,   6,   1,  4,  1,  2,  2,  1 ]),    # V Cpal...
	#	                   (4, True, [ 1,   1,   1,  2,  5,  2,  2,  1 ]),    # V Cpal e...
	#	                   (5, True, [ 1,   1,   1,  0,  1,  2,  0,  1 ]),    # V Cpal e +:0... [english.rul needed fixing]
	#	                   (6, True, [ 1,   1,   1,  7,  1,  2,  2,  1 ]),    # V C...
	#	                   (7, True, [ 1,   1,   1,  2,  8,  2,  2,  1 ]),    # V C e...
	#	                   (8, True, [ 1,   1,   1,  0,  1,  0,  0,  1 ]) ]), # V C e +:0... [english.rul needed fixing]
    def processRules(self, text):
        """
        Takes the currently typed in rules and processes them into the python kimmo
        format.  expects rules to be in c version of .rul file format.  needs to
        be file compatible.
        """
        # text = self.rules.get(1.0, Tkinter.END)
        testrule = []
        self.krules = []	
        self.ksubsets = []	
        self.kdefaults = []
        self.boundary_char = ''
        setgroup = ''
        rulegroup = ''
        rulerowcnt = 0
        rulecolcnt = 0
        kimmoRule = []



        ruleFrom = []
        ruleTo = []
        ruleTran = []

        anyset = ['','','','']


        tmpnode = {}		# a node and its edges
        tmpnode['node'] = ''
        tmpnode['features'] = ''
        tmpnode['edges'] = []		# list of the transitions
        tmpnode['edgenames'] = []	# matched array naming each transition

        tmpfsanodes = {}
        tmpfsanodes['nodes'] = []
        tmpfsanodes['name'] = ''
        self.fsasNodes = []	# list of nodes & their edges for the lexicon


        for line in text.split("\n"):
       	    # ''   None   	Genitive
            cleanLine = line.strip()



            if len(cleanLine) == 0 : continue		# blank line
            # this char can be a comment if it is not the boundary char.
            # yes, yes, it should be defined such that it is not in the alphabet at all
            # also boundary would need to be defined before ...
            elif (cleanLine[0] == '#') and (anyset[3] != '#'): continue		# a comment
            elif (cleanLine[0] == ';') and (anyset[3] != ';') : continue		# a comment
            else:
            	# lets do this one differently.
            	# lets break it first, then keep on looping until we find the next group (signified by a : )
            	p = re.compile(r"\s+")
            	items = []
            	items = p.split(cleanLine)
            	
            	# now handle subset keywords
            	# KimmoSubset('C', 'b c d f g h j k l m n p q r s t v w x y z'),
            	
            	if items[0] == 'SUBSET':
            		if items[1] == 'ALL': items[1] = '@'
            		self.ksubsets.append(
            			KimmoSubset(items[1], string.join(items[2:len(items)]," ") ))
            		# print items[1] + ' ' + string.join(items[2:len(items)]," ")
            		
            	# load up the fsa regexp based on alphabet	
            	# also set up the @ subset if alphabet is defined (old rule file style)
            	elif items[0] == 'ALPHABET': anyset[1] = string.join(items[1:len(items)]," ")
            	
            	elif items[0] == 'ANY': anyset[0] = items[1]
            	
            	elif items[0] == 'NULL': anyset[2] = items[1]
            	
            	# using the boundary char, set the final boundary & also add to the any set.
            	elif items[0] == 'BOUNDARY':
            		anyset[3] = items[1]
            		self.boundary_char = items[1]
            	
            	elif items[0] == 'DEFAULT':
            		self.kdefaults = [ KimmoDefaults(string.join(items[1:len(items)]," ")) ]
            		
            	elif items[0] == 'ARROWRULE':
            		# ARROWRULE 03:epenthesis1 0:e ==> [Csib (c h) (s h) y:i] +:0 _ s [+:0 #]
            		# KimmoArrowRule('03:epenthesis1',  '0:e ==> [Csib (c h) (s h) y:i] +:0 _ s [+:0 #]'),
            		# print items[1] + ' ' + string.join(items[2:len(items)]," ")
            		self.krules.append(
            			KimmoArrowRule(items[1],  string.join(items[2:len(items)]," "))
            			# KimmoArrowRule('05:y:i-spelling', 'y:i <=> @:C +:0? _ +:0 ~I')
            			)

            	elif items[0] == 'RULE':	# this is actually FSArules
            								# make compatible with rul files
            		
            		if rulegroup: self.guiError('error, fsa rule not finished')
            		
            		rulecolcnt = string.atoi(items[len(items)-1])
            		rulerowcnt = string.atoi(items[len(items)-2])
            		rulegroup = string.join(items[1:len(items)-2])
            		
            		# create the structure (for graphing) for storing the transitions
            		# of the fsas
            		tmpfsanodes = {}
            		tmpfsanodes['nodes'] = []
            		tmpfsanodes['name'] = rulegroup
            		
            		# add the fail node by default
            		tmpnode = {}		# a node and its edges
            		tmpnode['node'] = '0'
            		tmpnode['features'] = 'color="indianred1", style=filled, shape=box'
            		tmpnode['edges'] = []
            		tmpnode['edgenames'] = []
            		
            		tmpfsanodes['nodes'].append(tmpnode)
            		
            		
            		
            	elif rulegroup:

            		# assume TRUE rules for now
            		# non-char test; already stripped of whitespace
            		ct = re.compile('[^0-9:\.]')	# go with [A-Za-z]
            		# if text, then add to first lines of fsa
            			# get row1 and row2 of text & translate into x:y col format.
            			
            		# if a number and until number is equal to row count, add
            			# i.e. not text
            		if ((':' in items[0]) or ('.' in items[0])) and (not ct.match(items[0])):
            			# make sure to check for TRUE vs FALSE rows...
            			# sprint items[0][0:len(items[0])-1] + ' -- ' + string.join(items[1:len(items)], " ")
            			
            			if (items[0][len(items[0])-1] == ':') : finalstate = True
            			elif (items[0][len(items[0])-1] == '.') : finalstate = False
            			else :
            				self.guiError("FSA table failure -- 'final state defn'")
            				continue
            			
            			items[0] = items[0][0:len(items[0])-1]	# remove the ':'
            			
            			# convert to integers (instead of strings)
            			for x in range(rulecolcnt + 1): items[x] = string.atoi(items[x]) # including the first row number - i.e. '4:'
            			
            			# add this row.
            			kimmoRule.append((items[0], finalstate, items[1:len(items)]))
            			
            			# now make this row into graph transitions
            			tmpnode = {}		# a node and its edges
            			tmpnode['node'] = str(items[0])
            			tmpnode['features'] = 'shape=box, fillcolor="lavender blush", style=filled'
            			if finalstate and (items[0] == 1):
            				tmpnode['features'] = 'shape=circle, color="paleturquoise2", style=filled'
            			elif (items[0] == 1):
            				tmpnode['features'] = 'color="paleturquoise2", style=filled, shape=box'
            			elif (finalstate):
            				tmpnode['features'] = 'shape=circle,fillcolor="honeydew2", style=filled'
            			tmpnode['edges'] = []
            			tmpnode['edgenames'] = []
            			# add as strings
            			# add unique, but group edgenames together
            			
            			tmpitems = items[1:len(items)]
            			for i in range(len(tmpitems)):
            				if str(tmpitems[i]) in tmpnode['edges']:
            					# find the index j of the matching target
            					for j in range(len(tmpnode['edges'])):
            						if str(tmpnode['edges'][j]) == str(tmpitems[i]):
            							
            							m = re.match(r"(^|\\n)([^\\]*)$", tmpnode['edgenames'][j])
            							# instead use a regular expression...
            							# this should really be done in dotstring
            							            								
            							if not m:
            								tmpnode['edgenames'][j] += (',' + ruleTran[i])
            							elif (len(m.group(2)) >= 15):
            								tmpnode['edgenames'][j] += ('\\n ' + ruleTran[i])
            							else:
            								tmpnode['edgenames'][j] += (',' + ruleTran[i])
            				else:
            					tmpnode['edges'].append(str(tmpitems[i]))
            					tmpnode['edgenames'].append(ruleTran[i])
            					
            				
            			"""
            			for x in items[1:len(items)]:
            				# go through and check, already added?
            				# for i in range(len(tmpnode['edges'])):
            				# 	if tmpnode['edges'][i] == x:
            				# 		tmpnode['edgenames'][i] += "," +
            				
            				tmpnode['edges'].append(str(x))
            			for x in ruleTran: tmpnode['edgenames'].append(x)
            			"""
            			tmpfsanodes['nodes'].append(tmpnode)
            			
            			
            			# if number is equal to row count, then add total and reset rule group
            			if ( items[0] == rulerowcnt):
            				self.krules.append(
            					KimmoFSARule(str(rulerowcnt)+':'+rulegroup, string.join(ruleTran," "), kimmoRule))
            				
            				# add to the master graph list
            				self.fsasNodes.append(tmpfsanodes)
            				
            				
            				rulegroup = ''
            				rulerowcnt = 0
            				rulecolcnt = 0
            				ruleTran = []	# reset the translation array
            				kimmoRule = []	# resent the kimmo rules as well
            		
            		# the char class/translations
            		elif len(items) == rulecolcnt:
            			# old style has 2 rows, class from, class to
            			if len(ruleFrom) == 0: ruleFrom = items
            			elif len(ruleTo) == 0: ruleTo = items
            			
            			# if ruleTo is ruleFrom: continue
            			
            			if (len(ruleTo) != rulecolcnt) or (len(ruleFrom) != rulecolcnt): continue
            			else:
            				for x in range(rulecolcnt):
            					if ruleTo[x] == ruleFrom[x]: ruleTran.append(ruleTo[x])
            					else:
            						ruleTran.append(ruleFrom[x] + ':' + ruleTo[x])
            				
           				ruleTo = []
            				ruleFrom = []

        # take care of the anyset, if it was defined (make into a subset)
        if (anyset[0] and anyset[1]):
        	self.ksubsets.append(KimmoSubset(anyset[0], string.join(anyset[1:len(anyset)]," ") ))
        	
        # print self.fsasNodes
        	
		
# ----------- KIMMOPAIR ---------------
#
# -------------------------------------
class KimmoPair:
    """
    Input/Output character pair
    """
    def __init__(self, input_subset, output_subset):
        self._input = input_subset
        self._output = output_subset


    def input(self): return self._input
    def output(self): return self._output


    def __repr__(self):
        sI = self.input()
        sO = self.output()
        s = sI + ':' + sO
        return s


    def __eq__(self, other):
        return (_classeq(self, other) and
                self._input == other._input and
                self._output == other._output)


    def __hash__(self):
        return hash( (self._input, self._output,) )


    def matches(self, input, output, subsets, negatedOutputMatch=False):
        if not(self._matches(self.input(), input, subsets)): return False
        m = self._matches(self.output(), output, subsets)
        if negatedOutputMatch: return not(m)
        return m


    def _matches(self, me, terminal, subsets):
        if (me == terminal): return True
        if (me[0] == '~'):
            m = me[1:]
            if (m in subsets):
                return not(terminal in subsets[m])
            else:
                return False
        if (me in subsets):
            return terminal in subsets[me]
        else:
            return False

_kimmo_terminal_regexp    = '[a-zA-Z0-9\+\'\-\#\@\$\%\!\^\`\}\{]+' # \}\{\<\>\,\.\~ # (^|\s)?\*(\s|$) !!! * is already covered in the re tokenizer
_kimmo_terminal_regexp_fsa    = '[^:\s]+' # for FSA, only invalid chars are whitespace and :
                                          # '[a-zA-Z0-9\+\'\-\#\@\$\%\!\^\`\}\{\<\>\,\.\~\*]+'
_kimmo_terminal_regexp_ext= '~?' + _kimmo_terminal_regexp

_kimmo_defaults           = _kimmo_terminal_regexp + '|\:'
_kimmo_defaults_fsa       = _kimmo_terminal_regexp_fsa + '|\:'
_kimmo_rule               = _kimmo_terminal_regexp_ext + '|[\:\(\)\[\]\?\&\*\_]|<=>|==>|<==|/<='

_arrows = ['==>', '<=>', '<==', '/<=']


_special_tokens = ['(', ')', '[', ']', '*', '&', '_', ':']
_special_tokens.extend(_arrows)
_non_list_initial_special_tokens = [')', ']', '*', '&', '_', ':']
_non_list_initial_special_tokens.extend(_arrows)


def parse_pair_sequence(description,token_type):
    """Read the description, which should be in form [X|X:Y]+, and return a list of pairs"""

    if token_type == 'FSA':
    	desc = list(tokenize.regexp(description, _kimmo_defaults_fsa))
    else:
    	desc = list(tokenize.regexp(description, _kimmo_defaults))

    prev = None
    colon = False
    result = []
    for token in desc:
        if token == ':':
            if colon: raise ValueError('two colons in a row')
            if prev == None: raise ValueError('colon must follow identifier')
            colon = True
        elif colon:
            result.append(KimmoPair(prev, token))
            prev = None
            colon = False
        else:
            if prev:
                result.append(KimmoPair(prev, prev))
            prev = token
            colon = False
    if colon: raise ValueError('colon with no following identifier')
    if prev: result.append(KimmoPair(prev, prev))
    return result



class KimmoSubset:
    def __init__(self, name, description):
        self._name = name
        self._description = description
        self._subset = list(set(tokenize.regexp(description, _kimmo_terminal_regexp_fsa)))
    def name(self): return self._name
    def description(self): return self._description
    def subset(self): return self._subset
    def __repr__(self):
        return '<KimmoSubset %s: %s>' % (self.name(), self.description(),)

class KimmoDefaults:
    def __init__(self, description):
        self._description = description
        self._defaults = set()
        for p in parse_pair_sequence(description, ''):
            self.defaults().add(p)
    def defaults(self): return self._defaults
    def __repr__(self):
        return '<KimmoDefaults %s>' % (self._description,)

class KimmoRule:
    def pairs(self): raise RuntimeError('unimplemented: KimmoRule.pairs()')
    def right_advance(self, current_states, input, output, subsets):
        raise RuntimeError('unimplemented: KimmoRule.right_advance()')


class KimmoArrowRule:
    """
    Two level rule
    """

    def leftFSA(self): return self._left_fsa
    def rightFSA(self): return self._right_fsa
    def pairs(self): return self._pairs
    def arrow(self): return self._arrow
    def lhpair(self): return self._lhpair

    def __init__(self, name, description):
        self._name = name
        self._description = description
        self._negated = False
        self._pairs = set()
        desc = list(tokenize.regexp(description, _kimmo_rule))
        self._parse(desc)

    def __repr__(self):
        return '<KimmoArrowRule %s: %s>' % (self._name, self._description)

    def advance(self, fsa, current_states, input, output, subsets):
        """Returns a tuple of (next_states, contains_halt_state)"""
        result = []
        contains_halt_state = False
        for current_state in current_states:
            for next_state in fsa.forward_traverse(current_state):
                ok = False
                for pair in fsa._labels[(current_state, next_state)]:
                    if pair.matches(input, output, subsets):
                        ok = True
                        break
                if (ok):
                    if (next_state in fsa.finals()): contains_halt_state = True
                    if not(next_state in result): result.append(next_state)
        return (result, contains_halt_state)


    def right_advance(self, current_states, input, output, subsets):
        return self.advance(self.rightFSA(), current_states, input, output, subsets)

    def matches(self, input, output, subsets):
        """Does this rule's LHS match this input/output pair?


        If it doesn't, return None.  If it does, return True if the rule must pass, False if the rule must fail."""


        if (self.arrow() == '==>'):
            if self.lhpair().matches(input, output, subsets):
                return True
            else:
                return None
        elif (self.arrow() == '<=='):
            if self.lhpair().matches(input, output, subsets, negatedOutputMatch=True):
                return False
            else:
                return None
        elif (self.arrow() == '/<='):
            if self.lhpair().matches(input, output, subsets, negatedOutputMatch=False):
                return False
            else:
                return None
        elif (self.arrow() == '<=>'):
            if self.lhpair().matches(input, output, subsets, negatedOutputMatch=False):
                return True
            elif self.lhpair().matches(input, output, subsets, negatedOutputMatch=True):
                return False
            else:
                return None
        else:
            raise RuntimeError('unknown arrow: '+self.arrow())

    def _parse(self, tokens):

        (end_pair, tree)  = self._parse_pair(tokens, 0)
        lhpair = self._pair_from_tree(tree)
        self._lhpair = lhpair
        self._pairs.add(lhpair)

        end_arrow         = self._parse_arrow(tokens, end_pair)
        (end_left, lfsa)  = self._parse_context(tokens, end_arrow, True)
        end_slot          = self._parse_slot(tokens, end_left)
        (end_right, rfsa) = self._parse_context(tokens, end_slot, False)
        if not(end_right == len(tokens)):
            raise ValueError('unidentified tokens')

        self._left_fsa  = lfsa
        self._right_fsa = rfsa

    def _next_token(self, tokens, i, raise_error=False):
        if i >= len(tokens):
            if raise_error:
                raise ValueError('ran off end of input')
            else:
                return None
        return tokens[i]

    def _pair_from_tree(self, tree):
        if (tree.node != 'Pair'): raise RuntimeException('expected Pair, got ' + str(tree))
        if len(tree) == 1:
            return KimmoPair(tree[0], tree[0])
        else:
            return KimmoPair(tree[0], tree[2])

    def _parse_pair(self, tokens, i):
        # print 'parsing pair at ' + str(i)
        t1 = self._next_token(tokens, i, True)
        if t1 in _special_tokens: raise ValueError('expected identifier, not ' + t1)
        t2 = t1
        j = i + 1
        if self._next_token(tokens, j) == ':':
            t2 = self._next_token(tokens, j+1, True)
            if t2 in _special_tokens: raise ValueError('expected identifier, not ' + t2)
            j = j + 2
            tree = Tree('Pair', tokens[i:j])
        else:
            tree = Tree('Pair', [tokens[i]])
        #print str(self._pair_from_tree(tree)) + ' from ' + str(i) + ' to ' + str(j)
        return (j, tree)


    def _parse_arrow(self, tokens, i):
        self._arrow = self._next_token(tokens, i, True)
        if not(self.arrow() in _arrows):
            raise ValueError('expected arrow, not ' + self.arrow())
        #print 'arrow from ' + str(i) + ' to ' + str(i+1)
        return i + 1


    def _parse_slot(self, tokens, i):
        slot = self._next_token(tokens, i, True)
        if slot != '_':
            raise ValueError('expected _, not ' + slot)
        # print 'slot from ' + str(i) + ' to ' + str(i+1)
        return i + 1


    def _parse_context(self, tokens, i, reverse):
        (j, tree) = self._parse_list(tokens, i)
        if j == i: return (i, None)

        sigma = set()
        self._collect_alphabet(tree, sigma)
        fsa = FSA(sigma)
        final_state = self._build_fsa(fsa, fsa.new_state(), tree, reverse)
        fsa.set_final([final_state])
        #fsa.pp()
        dfa = fsa.dfa()
        #dfa.pp()
        dfa.prune()
        #dfa.pp()
        return (j, dfa)


    def _collect_alphabet(self, tree, sigma):
        if tree.node == 'Pair':
            pair = self._pair_from_tree(tree)
            sigma.add(pair)
            self._pairs.add(pair)
        else:
            for d in tree: self._collect_alphabet(d, sigma)


    def _parse_list(self, tokens, i, type='Cons'):
        # print 'parsing list at ' + str(i)
        t = self._next_token(tokens, i)
        if t == None or t in _non_list_initial_special_tokens:
            # print '  failing immediately '
            return (i, None)
        (j, s) = self._parse_singleton(tokens, i)
        (k, r) = self._parse_list(tokens, j, type)
        # print (k,r)
        if r == None:
            # print '  returning (%d, %s)' % (j, s)
            return (j, s)
        tree = Tree(type, [s, r])
        # print '  returning (%d, %s)' % (k, tree)
        return (k, tree)


    def _parse_singleton(self, tokens, i):
        # print 'parsing singleton at ' + str(i)
        t = self._next_token(tokens, i, True)
        j = i
        result = None
        if t == '(':
            (j, result) = self._parse_list(tokens, i + 1, 'Cons')
            if result == None: raise ValueError('missing contents of (...)')
            t = self._next_token(tokens, j, True)
            if t != ')': raise ValueError('missing final parenthesis, instead found ' + t)
            j = j + 1
        elif t == '[':
            (j, result) = self._parse_list(tokens, i + 1, 'Or')
            if result == None: raise ValueError('missing contents of [...]')
            t = self._next_token(tokens, j, True)
            if t != ']': raise ValueError('missing final bracket, instead found ' + t)
            j = j + 1
        elif t in _special_tokens:
            raise ValueError('expected identifier, found ' + t)
        else:
            (j, tree) = self._parse_pair(tokens, i)
            result = tree
        t = self._next_token(tokens, j)
        if t in ['*', '&', '?']:
            j = j + 1
            result = Tree(t, [result])
        return (j, result)


    def _build_fsa(self, fsa, entry_node, tree, reverse):
        if tree.node == 'Pair':
            return self._build_terminal(fsa, entry_node, self._pair_from_tree(tree))
        elif tree.node == 'Cons':
            return self._build_seq(fsa, entry_node, tree[0], tree[1], reverse)
        elif tree.node == 'Or':
            return self._build_or(fsa, entry_node, tree[0], tree[1], reverse)
        elif tree.node == '*':
            return self._build_star(fsa, entry_node, tree[0], reverse)
        elif tree.node == '&':
            return self._build_plus(fsa, entry_node, tree[0], reverse)
        elif tree.node == '?':
            return self._build_qmk(fsa, entry_node, tree[0], reverse)
        else:
            raise RuntimeError('unknown tree node'+tree.node)


    def _build_terminal(self, fsa, entry_node, terminal):
        new_exit_node = fsa.new_state()
        fsa.insert(entry_node, terminal, new_exit_node)
        #print '_build_terminal(%d,%s) -> %d' % (entry_node, terminal, new_exit_node)
        return new_exit_node


    def _build_plus(self, fsa, node, tree, reverse):
        node1 = self._build_fsa(fsa, node, tree[0], reverse)
        fsa.insert(node1, epsilon, node)
        return node1


    def _build_qmk(self, fsa, node, tree, reverse):
        node1 = fsa.new_state()
        node2 = self._build_fsa(fsa, node1, tree, reverse)
        node3 = fsa.new_state()
        fsa.insert(node, epsilon, node1)
        fsa.insert(node, epsilon, node3)
        fsa.insert(node2, epsilon, node3)
        return node3


    def _build_star(self, fsa, node, tree, reverse):
        node1 = fsa.new_state()
        node2 = self._build_fsa(fsa, node1, tree, reverse)
        node3 = fsa.new_state()
        fsa.insert(node, epsilon, node1)
        fsa.insert(node, epsilon, node3)
        fsa.insert(node2, epsilon, node1)
        fsa.insert(node2, epsilon, node3)
        return node3


    def _build_seq(self, fsa, node, tree0, tree1, reverse):
        (d0, d1) = (tree0, tree1)
        if reverse: (d0, d1) = (d1, d0)
        node1 = self._build_fsa(fsa, node, d0, reverse)
        node2 = self._build_fsa(fsa, node1, d1, reverse)
        # print '_build_seq(%d,%s,%s) -> %d,%d' % (node, tree0, tree1, node1, node2)
        return node2

    def _build_or(self, fsa, node, tree0, tree1, reverse):
        node0 = fsa.new_state()
        node1 = fsa.new_state()
        node2 = self._build_fsa(fsa, node0, tree0, reverse)
        node3 = self._build_fsa(fsa, node1, tree1, reverse)
        node4 = fsa.new_state()
        fsa.insert(node, epsilon, node0)
        fsa.insert(node, epsilon, node1)
        fsa.insert(node2, epsilon, node4)
        fsa.insert(node3, epsilon, node4)
        return node4


class KimmoFSARule:
    def __init__(self, name, pair_description, state_descriptions):
        self._name        = name
        self._pairs       = parse_pair_sequence(pair_description, 'FSA')
        self.transitions = {}
        self.is_final   = {}
        self._state_descriptions = state_descriptions
        # validate transitions
        for (index, is_final, next_state_array) in state_descriptions:
            if not(is_final == True or is_final == False):
                raise ValueError('each state description must take the form (index, True/False, [next_state_indices...]')

            if len(next_state_array) != len(self.pairs()):
                raise ValueError('transition array of wrong size '+ str(len(next_state_array)) + ' ' + str(len(self.pairs())))
            self.transitions[index] = next_state_array
            self.is_final[index] = is_final

    def name(self): return self._name
    def pairs(self): return self._pairs
    def start(self): return self._state_descriptions[0][0]
    def is_state(self, index): return self.transitions.has_key(index)


    def contains_final(self, indices):
        for i in indices:
            if self.is_final[i]: return True
        return False


    def sorted_pairs(self, subsets):
    	# pairs are ordered with the transition table, we want to order by the subset size.
    	# returns a list of pairs AND their indices for use.
    	# (index, pair) ; index represents the index of the position in the transitions table
    	
    	sorted_with_index = []
    	for idx, pair in enumerate(self.pairs()):	# enumerate lists all & assigns an index
    												# important to note that pairs() are in order
    												# corresponding with transition table
    		size1 = 1
    		size2 = 1
    		if pair.input() in subsets: size1 = len(subsets[pair.input()])
    		if pair.output() in subsets: size2 = len(subsets[pair.output()])
    		# setsize = size1 # + size2
    		sorted_with_index.append([idx,pair,size1,size2])
    	
    	sorted_with_index.sort(lambda x,y: self.mycompare(x[2],y[2],x[3],y[3]) ) # lambda x, y: x[2] - y[2])
    	return sorted_with_index


    # two field compare.
    def mycompare(self, x1, y1, x2=0, y2=0):
    	if x1 == y1: return x2-y2
    	else: return x1-y1

    def right_advance(self, current_states, input, output, subsets):

        next_states = []
        contains_halt_state = False
        for index in current_states:


            # flush the any states
            any_next_state = ''
            next_state_isset = 0
            any_next_states_ary = []

            for i, pair, size1, size2 in self.sorted_pairs(subsets): # enumerate(self.pairs()):
            	
                # print pair.__repr__()

                if pair.matches(input, output, subsets):
                	
                    # print input, output
                    # we want to temporarily store an any state (if one matches)
                    # only 1 any_next_state allowed
                    # '@'
                    # consequence of this is that moving to the back prevents discovery
                    # of of all possible enumerations in forced -> 0 state cases.  ie. 0:i -> 0
                    # recognition causes a problem, here's why.  this routine encounters @ before +:i
                    # it ignores it and goes on to 0:i.  0:i returns under yield, maintaining iterator
                    # state.  advance is called again, iterator state is resumed, but @ was already
                    # passed, and memory of that state is lost.
                    # it would be best if enumerate would just sort, but it cannot as it would lose ordering
                    # also invert under recognize is not properly recursing, as it never even sees the possible
                    # +:i option.
                    	# OLD CODE; PROBLEM SOLVED (ordering of subsets)
                    if 0: # ('@' in pair.__repr__()):
                    	# print 'any state match'
                    	# {col num, next state num (0 if fail), is final state}
                    	# if transition row is valid
                    	if self.transitions.has_key(self.transitions[index][i]): ft = self.is_final[self.transitions[index][i]]
                    	else : ft = ''
                    	any_next_states_ary.append([ i, self.transitions[index][i], ft, pair.__repr__() ] )
                    	if not any_next_state:
		                    any_next_state = self.transitions[index][i]
		

                    else:
	                    # if not an any state, add like usual
	                    # if not already in next_states, add
	                    # !!! but won't this break without evaluating @ when called several
	                    # times?  (i.e. our state is already in next_state
	                    next_state_isset = 1
	                    next_state = self.transitions[index][i]
	                    if self.transitions.has_key(next_state):
	                        if not(next_state in next_states):
	                            next_states.append(next_state)
	
	                            if self.is_final[next_state]: contains_halt_state = True
	                    break

        return (next_states, contains_halt_state)


    def __repr__(self):
        return '<KimmoFSARule %s>' % (self.name(), )


class KimmoWord:
    def __init__(self, letters, gloss, next_alternation=None):
        self._letters = letters
        self._gloss   = gloss
        self._next_alternation = next_alternation


    def __repr__(self):
        return '<KimmoWord %s: %s>' % (self.letters(), self.gloss())


    def letters(self): return self._letters
    def gloss(self): return self._gloss
    def next_alternation(self): return self._next_alternation


class KimmoLexicon:
    def __init__(self, name, words):
        self._name = name
        self._words = words
        self._trie = self.build_trie(words)


    def __repr__(self):
        return '<KimmoLexicon ' + self.name() + '>'


    def name(self): return self._name
    def words(self): return self._words
    def trie(self): return self._trie  # tree is ([KimmoWord], [ (char, sub-trie), ... ])


    def build_trie(self, words, word_position=0):
        if len(words) == 0: return ([], [])
        first_chars = {}
        for w in words:
            if len(w.letters()) <= word_position: continue
            fc = w.letters()[word_position]
            if first_chars.has_key(fc):
                first_chars[fc].append(w)
            else:
                first_chars[fc] = [ w ]
        sub_tries = []
        for c, sub_words in first_chars.items():
            sub_tries.append( (c, self.build_trie(sub_words, word_position+1)) )
        return ( [w for w in words if len(w.letters()) == word_position], sub_tries )


class KimmoAlternation:
    def __init__(self, name, lexicon_names):
        self._name = name
        self._lexicon_names = lexicon_names

    def __repr__(self):
        return '<KimmoAlternation ' + self.name() + ': ' + str(self.lexicon_names()) + '>'


    def name(self): return self._name
    def lexicon_names(self): return self._lexicon_names


class KimmoMorphology:
    def __init__(self, alternations, lexicons, start='Begin'):
        self.alternations = {}
        self.lexicons = {}
        self._start = start
        for a in alternations: self.alternations[a.name()] = a
        for l in lexicons: self.lexicons[l.name()] = l

    def set_boundary(self, boundary_char):
    	self.boundary = boundary_char

    def initial_state(self):
        return self._collect(self._start)


    def possible_next_characters(self, state):
        chars = set()
        self._possible_next_characters(state, chars)
        return chars

	# from the lexicon, return the next possible character from all words that match the current state
	# for instance, if lexicon has iti, ili, and iyi, and current state is first [i], then
	# this function will return a set of (t,l,y)
    def _possible_next_characters(self, state, chars):
        for s in state:
            if isinstance(s, KimmoLexicon):
                (words, sub_tries) = s.trie()
            else:
                (words, sub_tries) = s
            for w in words:
                self._possible_next_characters(self._collect(w.next_alternation()), chars)
            for c, sub_trie in sub_tries:
                chars.add(c)

    def _collect(self, name):
    	# print 'current alternation: ' + name
        if name == None:
            return []
        elif self.alternations.has_key(name):
            result = []
            for ln in self.alternations[name].lexicon_names():
                result.extend(self._collect(ln))
            return result
        elif self.lexicons.has_key(name):
            return [ self.lexicons[name] ]
        else:
            # raise ValueError('no lexicon or alternation named ' + name)
            return []

    def advance(self, state, char):
        result = []
        # print 'advance'

        for s in state:
            if isinstance(s, KimmoLexicon):
            	# print s.name()
                (words, sub_tries) = s.trie()
            else:
                (words, sub_tries) = s
            for w in words:
                for v in self._advance_through_word(w, char):
                    yield v
            for c, sub_trie in sub_tries:
                if c == char: result.append(sub_trie)
        if len(result) > 0:
            yield (result, [])
        # else:
        	# print 'No Matches in state '


    def _advance_through_word(self, word, char):
        for s in self.advance(self._collect(word.next_alternation()), char):
            state, words = s
            if word.gloss():
                yield (state, [word] + words)
            else:
                yield s

class KimmoRuleSet:
    def __init__(self, subsets, defaults, rules, null='0'):
        self.debug = False
        self._rules = rules
        self._pair_alphabet = set()
        self._subsets = {}
        self._null = null
        for s in subsets:
            self._subsets[s.name()] = s.subset()

        for kd in defaults:
            for pair in kd.defaults():
                # defaults shouldn't contain subsets
                if self.is_subset(pair.input()) or self.is_subset(pair.output()):
                    raise ValueError('default ' + str(pair) + ' contains subset')
                self._pair_alphabet.add( ( pair.input() , pair.output() ) )
        for r in self.rules():
            for kp in r.pairs():
                if (not (self.is_subset(kp.input()) or self.is_subset(kp.output()))):
                    self._pair_alphabet.add( ( kp.input(), kp.output() ) )

    def rules(self): return self._rules
    def subsets(self): return self._subsets
    def is_subset(self, key):
        return key[0] == '~' or key in self.subsets()

    def null(self): return self._null;


    def _evaluate_rule_left_context(self, rule, input, output):
        fsa = rule.leftFSA()
        if fsa == None: return True
        states = [ fsa.start() ]
        i = len(input) - 1
        while i >= 0:
            next_states = []
            (result, contains_halt_state) = rule.advance(fsa, states, input[i], output[i], self.subsets())
            if contains_halt_state: return True
            for s in result:
                if not(s in next_states): next_states.append(s)
            if (len(next_states) == 0): return False
            states = next_states
            i = i - 1
        return False

    def _debug_print_input_and_output(self, position, rule_states, morphological_state,
                                      input, output, this_input, this_output, invert):
        if (self.debug):
            #indent str
            padstring = ''
            for x in range(position): padstring = padstring + ' '

            print '%s%d  %s:%s \n' % (padstring, position, this_input, this_output),
            print '%s%d: Input:  ' % (padstring, position,),
            for i in input:
                print ' ' + i + ' ',
            if this_input:
                print '[' + this_input + ']...',
            print


            print '%s%d> Output: ' % (padstring, position,),
            for o in output:
                print ' ' + o + ' ',
            if this_output:
                print '<' + this_output + '>...',
            print


            # for (start, rule, fsa_states, required_truth_value) in rule_states:
            #    print '    {%d %s %s %s}' % (start, rule, fsa_states, required_truth_value)


            if False: # morphological_state:
                print '    possible input chars = %s' % invert.possible_next_characters(morphological_state)
                # print morphological_state


	# generate works by passing in the word at each position of the word
	# _generate is responsible for testing all the valid chars in the transition alphabet to see if
	# they are appropriate surface-underlying transitions.
	# it fails entirely if no valid transitions are found
	# if one is found, that is the one that is used.
	# essentially this is a possible word tree being expanded and failed on branches.
	# should return a list of matching words.
    def _generate(self, input_tokens, position, rule_states, morphological_state, input, output, result_str, result_words,
                  invert=False):
        # state is [ ( start, rule, states, required_truth_value ) ]
        # print 'morphological_state'
        # print morphological_state

	# if (self.debug) :
		# print '_generate'
		# print input_tokens, position, input, output, result_str, result_words
		# when at the last token or past it.
		
        if ((position >= len(input_tokens)) ): # and (not morphological_state)

            if (self.debug) : print '      AT END OF WORD'
        	# FOR RECOGNIZER
        	# this will yield some words twice, not all
        	# also, recognizer is failing to put on the added information like "+genetive"
        	
        	# we are at the end, so check to see if a boundary char is in the possible set
        	# and if so, add it and the remaining morphos
            if morphological_state:
            						
	            # print 'morpho'
	            possible_next_input_chars = invert.possible_next_characters(morphological_state)
	            # print 'possible_next_input_chars'
	            # print possible_next_input_chars
	            # change to boundary char, instead of hardcode
	            if ('0' in possible_next_input_chars) or ('#' in possible_next_input_chars):
	            	if '0' in possible_next_input_chars: boundary = '0'
	            	elif '#' in possible_next_input_chars: boundary = '#'
	            	
	            	# are at the end of the word, so we need to check and return those results
	            	# that contain the boundary char.
	            	
	            	# should only be one potential boundary word '0'
	            	# not correct, there can be more than one boundary word.
	            	for next_morphological_state, new_words in invert.advance(morphological_state, boundary):
	            		# yield result_str, result_words + new_words
	            		# print new_words
	            		# print next_morphological_state
	            		# for o in self._generate(input_tokens, position + 1, [] , next_morphological_state,
	            		#                    new_input, new_output, new_result_str,
	            		#                    result_words + new_words,
	            		#                    invert):
	            		#	yield o
                		yield result_str, result_words + new_words

	            # yield result_str, result_words

            else:
	            # GENERATION CASE
	            # print 'no-morpho'
	            self._debug_print_input_and_output(position, rule_states, morphological_state, input, output, None, None, invert)
	            for (start, rule, fsa_states, required_truth_value) in rule_states:
	                if isinstance(rule, KimmoArrowRule):
	                    truth_value = False # since it hasn't reached a halt state
	                elif isinstance(rule, KimmoFSARule):
	                    truth_value = rule.contains_final(fsa_states)
	
	                if (required_truth_value != truth_value):
	                    if (self.debug):
	                        print '    BLOCKED by rule {%d %s %s}' % (start, rule, required_truth_value)
	                        print fsa_states
	                    break
	                else:
	                    if 0: # (self.debug):
	                        print '    passed rule {%d %s %s}' % (start, rule, required_truth_value)
	
	            else:
	                if (self.debug):
	                    print '   SUCCESS!'
	                yield result_str, result_words
        else:
            if morphological_state: # recognizer; get the next possible surface chars that can result in
            						# the next char
                possible_next_input_chars = invert.possible_next_characters(morphological_state)
                # print 'possible_next_input_chars'
                # print possible_next_input_chars

            # foreach pair in our alphabet (includes per subset)
            # print self._pair_alphabet
            for pair_input, pair_output in self._pair_alphabet:

                if (pair_input != self.null() and morphological_state):
                    # if this pair does not apply, i.e. it is not in the possible
                    # chars from the lexicon
                    if not(pair_input in possible_next_input_chars):
                        continue

                if invert:
                	# check if the output of a transition is in the input string (input_tokens)
                    compare_token = pair_output
                else:
                    compare_token = pair_input

                if not(compare_token == self.null() or compare_token == input_tokens[position]): continue


                self._debug_print_input_and_output(position, rule_states, morphological_state,
                                                   input, output, pair_input, pair_output, invert)


                fail = None
                next_rule_states = []

                # first, evaluate currently activated rules
                # s is the current rule & its state
                rule_state_debug  = '	'
                for s in rule_states:

                    # advance one through each rule
                    (start, rule, fsa_state_set, required_truth_value) = s

                    current_state_str = '['
                    for x in fsa_state_set: current_state_str += str(x)
                    rule_state_debug += current_state_str

                    (next_fsa_state_set, contains_halt_state) = rule.right_advance(fsa_state_set, pair_input, pair_output,
                                                                                   self.subsets())

                    current_state_str = ''
                    for x in next_fsa_state_set: current_state_str += str(x)
                    if not current_state_str: current_state_str = '0 (FAIL)'
                    rule_state_debug += ('->' + current_state_str + '] ')

                    if (contains_halt_state == True and isinstance(rule, KimmoArrowRule)):
                        if (required_truth_value == False):
                            fail = s
                            break
                        else:
                            if (0): # (self.debug):
                                print '    passed rule {%d %s %s}' % (start, rule, required_truth_value)
                    elif (len(next_fsa_state_set) == 0):
                    	# if it isn't true, then it will have to fail, bcs we are at
                    	# the end of the state set.
                    	# truth is evaluated by following the states until the end.
                        if (required_truth_value == True):
                            fail = s
                            break
                        else:
                            if (0): # (self.debug):
                                print '    passed rule {%d %s %s}' % (start, rule, required_truth_value)
                    else:
                        next_rule_states.append( (start, rule, next_fsa_state_set, required_truth_value) )

                if (self.debug) : print rule_state_debug

                if (fail):
                    if (self.debug):
                        print '    BLOCKED by rule %s' % (fail,)
                    continue


                # activate new KimmoArrowRules
                for rule in self.rules():
                    if not(isinstance(rule, KimmoArrowRule)): continue

                    required_truth_value = rule.matches(pair_input, pair_output, self.subsets())
                    if required_truth_value == None: continue
                    left_value = self._evaluate_rule_left_context(rule, input, output)
                    if (left_value == False):
                        if (required_truth_value == True):
                            fail = rule
                        continue


                    if (rule.rightFSA()):
                        if (self.debug):
                            print '    adding rule {%d %s %s}' % (position, rule, required_truth_value)
                        next_rule_states.append( (position, rule, [ rule.rightFSA().start() ], required_truth_value) )
                    else:
                        if (required_truth_value == False):
                            fail = rule
                            continue
                        else:
                            if (0): # (self.debug):
                                print '    passed rule ' + str(rule)

                # if did not fail, call recursively on next chars
                if (fail == None):
                    new_position      = position
                    new_input         = input  + [pair_input]
                    new_output        = output + [pair_output]
                    new_result_str    = result_str

                    if (pair_input  != self.null()):
                        if invert:
                            new_result_str = result_str + pair_input
                        else:
                            new_position = position + 1
                    if (pair_output != self.null()):
                        if invert:
                            new_position = position + 1
                        else:
                            new_result_str = result_str + pair_output


                    # morph state & generation steps through a char at a time.
                    # as it is, it only yields its morph if there is a valid next morphology
                    if morphological_state and pair_input != self.null():
                        for next_morphological_state, new_words in invert.advance(morphological_state, pair_input):
                            # print 'ENTERING LEXICON '
                            for o in self._generate(input_tokens, new_position, next_rule_states, next_morphological_state,
                                                    new_input, new_output, new_result_str,
                                                    result_words + new_words,
                                                    invert):
                                yield o
                    else:
                        for o in self._generate(input_tokens, new_position, next_rule_states, morphological_state,
                                                new_input, new_output, new_result_str, result_words, invert):
                            yield o
                else:
                    if (self.debug):
                        print '    BLOCKED by rule ' + str(fail)

    def _initial_rule_states(self):
        return [ (0, rule, [ rule.start() ], True) for rule in self.rules() if isinstance(rule, KimmoFSARule)]

    def generate(self, input_tokens):
        """Generator: yields output strings"""
        for o, w in self._generate(input_tokens, 0, self._initial_rule_states(), None, [], [], '', None):
            yield o


    def recognize(self, input_tokens, morphology=None):
        """Recognizer: yields (input_string, input_words)"""
        morphology_state = None
        output_words = None
        invert = True
        if morphology:
            morphology_state = morphology.initial_state()
            output_words = []
            invert = morphology


        if not morphology_state:
            print "Bad Morphological State, failing recognition"
            return        	
        if (self.debug) : print 'recognize: ' + input_tokens
#        print output_words
        for o in self._generate(input_tokens, 0, self._initial_rule_states(), morphology_state, [], [], '',
                                output_words, invert):
            yield o	# yielding a list of possible words.


def _generate_test(s, input):
    resultlist = '%s -> ' % (input,),
    padlevel = len(input) + 4
    padstring = ''
    # for x in range(padlevel): padstring = padstring + ' '

    tmplist = '%s' % ('***NONE***'),
    for o in s.generate(input):
    	tmplist = '%s%s\n' % (padstring,o,),
    	resultlist = resultlist + tmplist
    	padstring = ''
    	for x in range(padlevel): padstring = padstring + ' '
    	tmplist = '%s' % (''),
    resultlist = resultlist + tmplist

    return resultlist


def _recognize_test(s, input, morphology=None):
    resultlist =  '%s <- ' % (input,),
    padlevel = len(input) + 4
    padstring = ''
    # for x in range(padlevel): padstring = padstring + ' '

    tmplist = '%s' % ('***NONE***'),
    for o, w in s.recognize(input, morphology):
        if w:
            # print
            tmplist = '\n  %s   %s \n' % (o, w),
            resultlist = resultlist + tmplist
        else:
            tmplist = '%s%s \n' % (padstring,o,),
            resultlist = resultlist + tmplist

        padstring = ''
        for x in range(padlevel): padstring = padstring + ' '
        tmplist = '%s' % (''),
    # print
    # q = re.compile('(\{|\})')
    # q.sub("", resultstring[0])
    resultlist = resultlist + tmplist

    return resultlist

def read_kimmo_file(filename, gui=None):
    path = os.path.expanduser(filename)
    try:
        f = open(path, 'r')
    except IOError, e:
        path = os.path.join(get_basedir(), "kimmo", filename)
        try:
            f = open(path, 'r')
        except IOError, e:
            if gui:
                gui.guiError(str(e))
            else:
                print str(e)
            print "FAILURE"
            return ""
    print "Loaded:", path
    return f

# MAIN
# if __name__ == '__main__': KimmoGUI(None, None)
# if __name__ == '__main__': tkImageView("")
if __name__ == '__main__':
	filename_lex = ''
	filename_rul = ''
	filename_batch_test = ''
	recognize_string = ''
	generate_string = ''
	console_debug = 0
	
	for x in sys.argv:
		# if -r/g is defined (recognize or generate word)
		# or batch file is defined
		# run in commandline mode.
		
		if ".lex" in x: filename_lex = x
		elif ".rul" in x: filename_rul = x
		elif ".batch" in x: filename_batch_test = x
		elif x[0:3] == "-r:": recognize_string = x[3:len(x)]
		elif x[0:3] == "-g:": generate_string = x[3:len(x)]
		elif x == "debug": console_debug = 1
		

	print 'Tips:'
	print 'kimmo.cfg is loaded by default, so if you name your project that, '
	print "it will be loaded at startup\n"
	
	print 'For commandline operation:'
	print '		(for instance if you want to use a different editor)'
	print "To Recognize:"
	print "	% python kimmo.py english.lex english.rul -r:cats"
	print "To Generate:"
	print "	% python kimmo.py english.lex english.rul -g:cat+s"
	print "To Batch Test:"
	print "	% python kimmo.py english.lex english.rul english.batch_test"
	print "With Debug and Tracing:"
	print "	% python kimmo.py english.lex english.rul -r:cats debug\n"

	
	# print filename_lex	
	# print filename_rul
	# print filename_batch_test
	# print recognize_string
	# print generate_string
	
	
	if (recognize_string or generate_string or filename_batch_test) and filename_rul:
		kimmoinstance = KimmoControl("","",filename_lex,filename_rul,console_debug)
		
		# creation failed, stop
		if not kimmoinstance.ok :
			print kimmoinstance.errors
			sys.exit()

		
		if recognize_string:
			recognize_results = kimmoinstance.recognize(recognize_string)
			print recognize_results
		
		if generate_string:
			generate_results = kimmoinstance.generate(generate_string)
			print generate_results 	# remember to format
			
		if filename_batch_test:		# run a batch
			kimmoinstance.batch(filename_batch_test)
	
	else:
		KimmoGUI(None, None)
	
	# constructor takes arguments:
	# KimmoControl(lexicon_string, rule_string, lexicon_filename, rule_filename, debug)
	# the constructor requires both lexicon and rules for recognition.
	# you can provide either the file contents as a string, or as a filename.
	# if only used to generate, only a rule file/string is necessary.
	
	# kimmoinstance = KimmoControl("","",'','./englex/english.rul',0)
	# kimmoinstance = KimmoControl("","",'kimmo.lex','kimmo.rul',0)
	# generate_results = kimmoinstance.generate("cat+s")
	# print generate_results
	
	# recognize_results = kimmoinstance.recognize("cats")
	# print recognize_results

