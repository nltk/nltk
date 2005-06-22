\_sh v3.0  445  Readme Notes

\id SDF Sample
\s Eastern Aramaic Script
\p This sample shows the use of the SDF (Script Definition File) system. The
script used for demonstration is the Eastern Aramaic script. It is written
from right to left in a cursive style with characters joined together, except
for certain characters that do not join to the following character. The main
characters are consonants, with diacritic marks used to show vowels.
\p The window at the upper left shows a sample file text in the Eastern
Aramaic script.
\p If the text is not shown in the script, close Shoebox and install the font
NISIBUS.TTF from the sample project folder. Then run Shoebox again
to see the script rendered correctly.
\s Right-to-Left Scripts in Shoebox
\p Shoebox supports right-to-left text entry and editing. You can experiment
with inserting and deleting characters to see how this works. The window
is set to Auto Wrap, so if you insert or delete text you will see the
paragraph rewrap. Shoebox allows mixtures of right-to-left fields and
left-to-right fields in the same file. For example, the \id field is left-to-right.
\p The window in the lower left shows a word list of four sample text files,
displayed in browse view. It illustrates that when a right-to-left field is
shown in a browse view, the text is show right justified.
\s Setup of a Language for SDF
\p The SDF setup information for a script is contained in the language
encoding. To see the setup for the Aramaic script, select Project,
Language Encodings, and choose the Aramic language. Choose the
Options tab and then choose Advanced Options.
\s Rendering DLL
\p The Advanced Options dialog box says that text in this language is to be
rendered using RENDER.DLL. This is the DLL that performs SDF
rendering. It is provided with the Shoebox program as RENDER16.DLL
and RENDER32.DLL. Shoebox choosed the correct DLL based on
which version of the program is being run.
\s SDF Table
\p The dialog box says that the rendering DLL should use the table
NISIBUS.SDF. This is a file in the project folder. It is built and edited
with the SDFE (SDF Editor) program, which is provided with Shoebox.
\s Right-to-Left
\p The dialog box has a check box that says the script is right-to-left. This
causes text in the language to be displayed and sorted from right-to-left.
SDF can be used for rendering scripts of either direction.
\p Press the Help button in the dialog box for more information on rendering.
When you have looked at it, close the help, and press cancel once to
move from the Advanced Language Options dialog box back to the
Language Encoding Properties.
\s Keyboard
\p Notice that the Keyboard shows Assyrian. This keyboard is in the
Keyman file ASY.KMN, in the sample project folder. Keyman
keyboards are often used in SDF setups to do the keyboard layout. This
allows the underlying encoding to be different from the keys pressed. It
also allows different keyboards. For example, this sample includes two
Keyman keyboards, one with a traditional keyboard layout (ASY.KMN),
and the other arranged by letter sounds (ASYPHO.KMN). If you are
interested enough to see this in action, you should close Shoebox, run
Keyman, load the two Assyrian keyboards, and then run Shoebox again.
You can then choose either of the two keyboards in the Language
Encoding Options box.
\p Keyman does not have a way to display keyboard layouts, so you will
have to read the .KMN files to see what the layouts do. The files contain
lots of comments giving the letter names, so they give good layout
information.
\s SDF Editor
\p The SDF Editor is used to set up a new SDF script file or modify an
existing one. It shows letter names, underlying codes, and rendered
appearance. To see this in action, run the SDFE program from the
Shoebox program folder. Choose File, Open and open the file
NISIBUS.SDF in this sample project folder. You will see a display with
comment, underlying code, and the four rendered forms of each
character. You can move up and down the list to see the entire rendering
setup. Choose Help for more information about how to use the program.
Close the SDFE program when you are finished looking at the sample file.
\s Export to WinWord for Printing
\p SDF is used to render text both for screen display and for RTF export.
The result is that RTF export gives a form that can be formatted and
printed using WinWord. This works for both WinWord 6 and WinWord
97. For right-to-left text, the text is output from left to right so that Word
can flow the text into paragraphs. Picture spaces and other custom
formatting can be done. After the formatting is all done, a macro is run
that reverses every line of right-to-left text so that it reads correctly.
\p To see how this works, select the sample text file and choose File,
Export. You will see a list of Export Processes. Select the Asy NT RTF
process and choose OK. Give a file name of Phil1.rtf and choose OK.
You will see the file output and the document open in WinWord. The
output process has already attached a template with the right-to-left
reverse macro. (The sample template works best on Word 6 or Word 7.)
Choose Tools, ReverseRightToLeftText. You will see a progress bar,
WinWord will close and reopen automatically, and you will see the text in
correct right-to-left order ready to print. Close WinWord and return to
Shoebox.
\p To see the details of how export is done, select the sample text file and
choose File, Export. Then choose Processes, select Asy NT RTF and
choose Modify. You will see that it exports all fields, uses a CC table
called ASYOUT.CCT, and attaches a template named AsyNT6.dot. For
WinWord 97, you would use a template created in WinWord 97. For
information on how to create a template for your own text, see the file 
RTLREV.TXT in the DOC folder under the folder containing the
Shoebox program.
