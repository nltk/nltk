import Tkinter
from nltk.draw import tree as drawTree, CanvasFrame

"""A class that draws parse trees in a simple Tk window."""

class TreeView:
	def __init__(self, trees, root=None):
		newroot = False
		if root is None:
			root = Tkinter.Tk()
			window = root
			newroot = True
		else:
			window = Tkinter.Toplevel(root)
		
		window.title("Parse Tree")
		window.geometry("600x400")
		self.cf = CanvasFrame(window)
		self.cf.pack(side='top', expand=1, fill='both')
		buttons = Tkinter.Frame(window)
		buttons.pack(side='bottom', fill='x')

		self.spin = Tkinter.Spinbox(buttons, from_=1, to=len(trees),
			command=self.showtree, width=3)
		if len(trees) > 1: self.spin.pack(side='left')
		self.label = Tkinter.Label(buttons, text="of %d" % len(trees))
		if len(trees) > 1: self.label.pack(side='left')
		self.done = Tkinter.Button(buttons, text="Done", command=window.destroy)
		self.done.pack(side='right')
		self.printps = Tkinter.Button(buttons, text="Print to Postscript", command=self.cf.print_to_file)
		self.printps.pack(side='right')
		
		self.trees = trees
		self.treeWidget = None
		self.showtree()
		if newroot: root.mainloop()
	
	def showtree(self):
		try: n = int(self.spin.get())
		except ValueError: n=1
		if self.treeWidget is not None: self.cf.destroy_widget(self.treeWidget)
		self.treeWidget = drawTree.TreeWidget(self.cf.canvas(),
		self.trees[n-1], draggable=1, shapeable=1)
		self.cf.add_widget(self.treeWidget, 0, 0)
	
