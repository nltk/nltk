;;; doctest-mode.el --- Major mode for editing Python doctest files

;; Copyright (C) 2004  Edward Loper

;; Author:     Edward Loper
;; Maintainer: edloper@alum.mit.edu
;; Created:    Aug 2004
;; Keywords:   python doctest unittest test docstring

(defconst doctest-version "0.3"
  "`doctest-mode' version number.")

;; This software is provided as-is, without express or implied
;; warranty.  Permission to use, copy, modify, distribute or sell this
;; software, without fee, for any purpose and by any individual or
;; organization, is hereby granted, provided that the above copyright
;; notice and this paragraph appear in all copies.

;; This is a major mode for editing text files that contain Python
;; doctest examples.  Doctest is a testing framework for Python that
;; emulates an interactive session, and checks the result of each
;; command.  For more information, see the Python library reference:
;; <http://docs.python.org/lib/module-doctest.html>

;; Known bugs:
;; - Some places assume prompts are 4 chars (but they can be 3
;;   if they're bare).
;; - String literals are not colored correctly.  (We need to color
;;   string literals on source lines, but *not* output lines or
;;   text lines; this is hard to do.)
;; - Output lines starting with "..." are mistakenly interpreted
;;   as (continuation) source lines.

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Customizable Constants
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defgroup doctest nil
  "Support for the Python doctest framework"
  :group 'languages
  :prefix "doctest-")

(defcustom doctest-default-margin 4
  "The default pre-prompt margin for doctest examples."
  :type 'integer
  :group 'doctest)

(defcustom doctest-avoid-trailing-whitespace t
  "If true, then delete trailing whitespace when inserting a newline."
  :type 'boolean
  :group 'doctest)

(defcustom doctest-temp-directory
  (let ((ok '(lambda (x)
	       (and x
		    (setq x (expand-file-name x)) ; always true
		    (file-directory-p x)
		    (file-writable-p x)
		    x))))
    (or (funcall ok (getenv "TMPDIR"))
	(funcall ok "/usr/tmp")
	(funcall ok "/tmp")
	(funcall ok "/var/tmp")
	(funcall ok  ".")
	(error (concat "Couldn't find a usable temp directory -- "
		       "set `doctest-temp-directory'"))))
	 
  "*Directory used for temporary files created when running doctest.
By default, the first directory from this list that exists and that you
can write into: the value (if any) of the environment variable TMPDIR,
/usr/tmp, /tmp, /var/tmp, or the current directory."
  :type 'string
  :group 'doctest)

(defcustom hide-example-source t
  "If true, then don't display the example source code for each 
failure in the results buffer."
  :type 'boolean
  :group 'doctest)

(defcustom doctest-python-command "python"
  "Shell command used to start the python interpreter"
  :type 'string
  :group 'doctest)

(defcustom doctest-results-buffer-name "*doctest-output*"
  "The name of the buffer used to store the output of the doctest
command."
  :type 'string
  :group 'doctest)

(defcustom doctest-optionflags '()
  "Option flags for doctest"
  :group 'doctest
  :type '(repeat (choice (const :tag "Select an option..." "")
                         (const :tag "Normalize whitespace"
                                "NORMALIZE_WHITESPACE")
                         (const :tag "Ellipsis"
                                "ELLIPSIS")
                         (const :tag "Don't accept True for 1"
                                DONT_ACCEPT_TRUE_FOR_1)
                         (const :tag "Don't accept <BLANKLINE>"
                                DONT_ACCEPT_BLANKLINE)
                         (const :tag "Ignore Exception detail"
                                IGNORE_EXCEPTION_DETAIL)
                         (const :tag "Report only first failure"
                                REPORT_ONLY_FIRST_FAILURE)
                         )))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Fonts
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defface doctest-prompt-face
  '((((class color) (background dark))
     (:foreground "#68f"))
    (t (:foreground "#226")))
  "Face for Python prompts in doctest examples."
  :group 'doctest)

(defface doctest-output-face
  '((((class color) (background dark))
     (:foreground "#afd"))
    (t (:foreground "#262")))
  "Face for the output of doctest examples."
  :group 'doctest)

(defface doctest-output-marker-face
  '((((class color) (background dark))
     (:foreground "#0f0"))
    (t (:foreground "#080")))
  "Face for markers in the output of doctest examples."
  :group 'doctest)

(defface doctest-output-traceback-face
  '((((class color) (background dark))
     (:foreground "#f88"))
    (t (:foreground "#622")))
  "Face for traceback headers in the output of doctest examples."
  :group 'doctest)

(defface doctest-results-divider-face
  '((((class color) (background dark))
     (:foreground "#08f"))
    (t (:foreground "#00f")))
  "Face for dividers in the doctest results window."
  :group 'doctest)

(defface doctest-results-loc-face
  '((((class color) (background dark))
     (:foreground "#0f8"))
    (t (:foreground "#084")))
  "Face for location headers in the doctest results window."
  :group 'doctest)

(defface doctest-results-header-face
  '((((class color) (background dark))
     (:foreground "#8ff"))
    (t (:foreground "#088")))
  "Face for sub-headers in the doctest results window."
  :group 'doctest)

(defface doctest-results-selection-face
  '((((class color) (background dark))
     (:foreground "#ff0" :background "#008"))
    (t (:background "#088" :foreground "#fff")))
  "Face for selected failure's location header in the results window."
  :group 'doctest)

(defface doctest-selection-face
  '((((class color) (background dark))
     (:foreground "#ff0" :background "#00f" :bold t))
    (t (:foreground "#f00")))
  "Face for selected example's prompt"
  :group 'doctest)

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Constants
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defconst doctest-prompt-re
  "^\\([ \t]*\\)\\(>>> ?\\|[.][.][.] ?\\)\\([ \t]*\\)"
  "Regular expression for doctest prompts.  It defines three groups:
the pre-prompt margin; the prompt; and the post-prompt indentation.")

(defconst doctest-open-block-re
  "[^\n]+:[ \t]*\\(#.*\\)?$"
  "Regular expression for a line that opens a block")

(defconst doctest-close-block-re
  "\\(return\\|raise\\|break\\|continue\\|pass\\)\\b"
  "Regular expression for a line that closes a block")

(defconst doctest-outdent-re
  (concat "\\(" (mapconcat 'identity
			   '("else:"
			     "except\\(\\s +.*\\)?:"
			     "finally:"
			     "elif\\s +.*:")
			   "\\|")
	  "\\)")
  "Regular expression for a line that should be outdented.  Any line
that matches `doctest-outdent-re', but does not follow a line matching
`doctest-no-outdent-re', will be outdented.")

(defconst doctest-no-outdent-re
  (concat
   "\\("
   (mapconcat 'identity
	      (list "try:"
		    "except\\(\\s +.*\\)?:"
		    "while\\s +.*:"
		    "for\\s +.*:"
		    "if\\s +.*:"
		    "elif\\s +.*:"
                    "\\(return\\|raise\\|break\\|continue\\|pass\\)[ \t\n]"
		    )
	      "\\|")
	  "\\)")
  "Regular expression matching lines not to outdent after.  Any line
that matches `doctest-outdent-re', but does not follow a line matching
`doctest-no-outdent-re', will be outdented.")

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Colorization support (font-lock mode)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Define the font-lock keyword table.
(defconst doctest-font-lock-keywords
  (let ((prompt "^[ \t]*\\(>>>\\|\\.\\.\\.\\)")
        (kw1 (mapconcat 'identity
			'("and"      "assert"   "break"   "class"
			  "continue" "def"      "del"     "elif"
			  "else"     "except"   "exec"    "for"
			  "from"     "global"   "if"      "import"
			  "in"       "is"       "lambda"  "not"
			  "or"       "pass"     "print"   "raise"
			  "return"   "while"    "yield"
			  )
			"\\|"))
	(kw2 (mapconcat 'identity
			'("else:" "except:" "finally:" "try:")
			"\\|"))
	(kw3 (mapconcat 'identity
			'("ArithmeticError" "AssertionError"
			  "AttributeError" "DeprecationWarning" "EOFError"
			  "Ellipsis" "EnvironmentError" "Exception" "False"
			  "FloatingPointError" "FutureWarning" "IOError"
			  "ImportError" "IndentationError" "IndexError"
			  "KeyError" "KeyboardInterrupt" "LookupError"
			  "MemoryError" "NameError" "None" "NotImplemented"
			  "NotImplementedError" "OSError" "OverflowError"
			  "OverflowWarning" "PendingDeprecationWarning"
			  "ReferenceError" "RuntimeError" "RuntimeWarning"
			  "StandardError" "StopIteration" "SyntaxError"
			  "SyntaxWarning" "SystemError" "SystemExit"
			  "TabError" "True" "TypeError" "UnboundLocalError"
			  "UnicodeDecodeError" "UnicodeEncodeError"
			  "UnicodeError" "UnicodeTranslateError"
			  "UserWarning" "ValueError" "Warning"
			  "ZeroDivisionError" "__debug__"
			  "__import__" "__name__" "abs" "apply" "basestring"
			  "bool" "buffer" "callable" "chr" "classmethod"
			  "cmp" "coerce" "compile" "complex" "copyright"
			  "delattr" "dict" "dir" "divmod"
			  "enumerate" "eval" "execfile" "exit" "file"
			  "filter" "float" "getattr" "globals" "hasattr"
			  "hash" "hex" "id" "input" "int" "intern"
			  "isinstance" "issubclass" "iter" "len" "license"
			  "list" "locals" "long" "map" "max" "min" "object"
			  "oct" "open" "ord" "pow" "property" "range"
			  "raw_input" "reduce" "reload" "repr" "round"
			  "setattr" "slice" "staticmethod" "str" "sum"
			  "super" "tuple" "type" "unichr" "unicode" "vars"
			  "xrange" "zip")
			"\\|"))
        (pseudokw (mapconcat 'identity
                        '("self" "None" "True" "False" "Ellipsis")
                        "\\|"))
        (brk "\\([ \t(]\\|$\\)")
	)
    `(
      ;; The following pattern colorizes source lines.  In particular,
      ;; it first matches prompts, and then looks for any of the
      ;; following matches *on the same line* as the prompt.  It uses
      ;; the form:
      ;;
      ;;   (MATCHER MATCH-HIGHLIGHT
      ;;            (ANCHOR-MATCHER nil nil MATCH-HIGHLIGHT)
      ;;            ...
      ;;            (ANCHOR-MATCHER nil nil MATCH-HIGHLIGHT))
      ;;
      ;; See the variable documentation for font-lock-keywords for a
      ;; description of what each of those means.
      (,prompt (1 'doctest-prompt-face)
               ;; classes
               ("\\b\\(class\\)[ \t]+\\([a-zA-Z_]+[a-zA-Z0-9_]*\\)"
                nil nil (1 'font-lock-keyword-face)
                (2 'font-lock-type-face))
               ;; functions
               ("\\b\\(def\\)[ \t]+\\([a-zA-Z_]+[a-zA-Z0-9_]*\\)"
                nil nil (1 'font-lock-keyword-face) (2 'font-lock-type-face))
               ;; keywords
               (,(concat "\\b\\(" kw1 "\\)" brk)
                nil nil (1 'font-lock-keyword-face))
               ;; builtins when they don't appear as object attributes
               (,(concat "\\(\\b\\|[.]\\)\\(" kw3 "\\)" brk)
                nil nil (2 'font-lock-keyword-face))
               ;; block introducing keywords with immediately
               ;; following colons.  Yes "except" is in both lists.
               (,(concat "\\b\\(" kw2 "\\)" brk)
                nil nil (1 'font-lock-keyword-face))
               ;; `as' but only in "import foo as bar"
               ("[ \t]*\\(\\bfrom\\b.*\\)?\\bimport\\b.*\\b\\(as\\)\\b"
                nil nil (2 'font-lock-keyword-face))
               ;; pseudo-keywords
               (,(concat "\\b\\(" pseudokw "\\)" brk)
                nil nil (1 'font-lock-keyword-face))
               ;; comments
               ("\\(#.*\\)"
                nil nil (1 'font-lock-comment-face)))

      ;; The following pattern colorizes output lines.  In particular,
      ;; it uses doctest-output-line-matcher to check if this is an
      ;; output line, and if so, it colorizes it, and any special
      ;; markers it contains.
      (doctest-output-line-matcher
       (0 'doctest-output-face t)
       ("\\.\\.\\." (beginning-of-line) (end-of-line)
	(0 'doctest-output-marker-face t))
       ("<BLANKLINE>" (beginning-of-line) (end-of-line)
	(0 'doctest-output-marker-face t))
       ("^Traceback (most recent call last):" (beginning-of-line) (end-of-line)
	(0 'doctest-output-traceback-face t))
       ("^Traceback (innermost last):" (beginning-of-line) (end-of-line)
	(0 'doctest-output-traceback-face t))
       )

      ;; A PS1 prompt followed by a non-space is an error.
      ("^[ \t]*\\(>>>[^ \t\n][^\n]*\\)" (1 'font-lock-warning-face t))

      ;; Selected example (to highlight selected failure)
      (doctest-selection-matcher (0 'doctest-selection-face t))
      ))
  "Expressions to highlight in Doctest mode.")

(defun doctest-output-line-matcher (limit)
  "A `font-lock-keyword' MATCHER that returns t if the current 
line is the expected output for a doctest example, and if so, 
sets `match-data' so that group 0 spans the current line."
  ;; The real work is done by find-doctest-output-line.
  (when (find-doctest-output-line limit)
    ;; If we found one, then mark the entire line.
    (beginning-of-line)
    (search-forward-regexp "[^\n]*" limit)))

;; [XX] Under construction.
(defun doctest-selection-matcher (limit)
  (let (found-it)
    (while (and (not found-it) 
                (search-forward-regexp "^[ \t]*\\(>>>\\|[.][.][.]\\)"
                                       limit t))
      (if (get-text-property (point) 'doctest-selected)
          (setq found-it t)))
    found-it))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Source line indentation
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defun doctest-indent-source-line (&optional dedent-only)
  "Re-indent the current line, as doctest source code.  I.e., add a
prompt to the current line if it doesn't have one, and re-indent the
source code (to the right of the prompt).  If `dedent-only' is true,
then don't increase the indentation level any."
  (interactive "*")
  (let ((indent-end nil))
    (save-excursion
      (beginning-of-line)
      (let ((new-indent (doctest-current-source-line-indentation dedent-only))
            (new-margin (doctest-current-source-line-margin))
            (line-had-prompt (looking-at doctest-prompt-re)))
        ;; Delete the old prompt (if any).
        (when line-had-prompt
          (goto-char (match-end 1))
          (delete-char 4))
        ;; Delete the old indentation.
        (delete-backward-char (skip-chars-forward " \t"))
        ;; If it's a continuation line, or a new PS1 prompt,
        ;; then copy the margin.
        (when (or new-indent (not line-had-prompt))
          (beginning-of-line)
          (delete-backward-char (skip-chars-forward " \t"))
          (insert-char ?\  new-margin))
        ;; Add the new prompt.
        (insert-string (if new-indent "... " ">>> "))
        ;; Add the new indentation
        (if new-indent (insert-char ?\  new-indent))
        (setq indent-end (point))))
    ;; If we're left of the indentation end, then move up to the
    ;; indentation end.
    (if (< (point) indent-end) (goto-char indent-end))))

(defun doctest-current-source-line-indentation (&optional dedent-only)
  "Return the post-prompt indent to use for this line.  This is an
integer for a continuation lines, and nil for non-continuation lines."
  (save-excursion
    (let ((prev-line-indent 0)
          (curr-line-indent 0)
          (prev-line-opens-block nil)
          (prev-line-closes-block nil)
          (curr-line-outdented nil))
      ;; Examine this doctest line.
      (beginning-of-line)
      (when (looking-at doctest-prompt-re)
          (setq curr-line-indent (- (match-end 3) (match-beginning 3)))
	  (goto-char (match-end 3)))
      (setq curr-line-outdented (looking-at doctest-outdent-re))
      ;; Examine the previous line.
      (when (= (forward-line -1) 0) ; move up a line
	(when (looking-at doctest-prompt-re) ; is it a source line?
	  (let ((indent-beg (column-at-char (match-beginning 3)))
		(indent-end (column-at-char (match-end 3))))
	    (setq prev-line-indent (- indent-end indent-beg))
	    (goto-char (match-end 3))
	    (if (looking-at doctest-open-block-re)
		(setq prev-line-opens-block t))
	    (if (looking-at doctest-close-block-re)
		(setq prev-line-closes-block t))
	    (if (looking-at doctest-no-outdent-re)
		(setq curr-line-outdented nil))
	    )))
      (let ((indent (+ prev-line-indent
                       (if curr-line-outdented -4 0)
                       (if prev-line-opens-block 4 0)
                       (if prev-line-closes-block -4 0))))
	;; If dedent-only is true, then make sure we don't indent.
	(when dedent-only 
	  (setq indent (min indent curr-line-indent)))
	;; If indent=0 and we're not outdented, then set indent to
	;; nil (to signify the start of a new source example).
	(when (and (= indent 0) (not curr-line-outdented))
	  (setq indent nil))
	;; Return the indentation.
	indent))))

(defun doctest-current-source-line-margin ()
  "Return the pre-prompt margin to use for this source line.  This is
copied from the most recent source line, or set to
`doctest-default-margin' if there are no preceeding source lines."
  (save-excursion
    (beginning-of-line)
    (if (search-backward-regexp doctest-prompt-re nil t)
        (let ((margin-beg (column-at-char (match-beginning 1)))
              (margin-end (column-at-char (match-end 1))))
          (- margin-end margin-beg))
      doctest-default-margin)))

(defun doctest-electric-backspace ()
  "Delete the preceeding character, level of indentation, or
prompt.  

If point is at the leftmost column, delete the preceding newline.

Otherwise, if point is at the first non-whitespace character
following an indented source line's prompt, then reduce the
indentation to the next multiple of 4; and update the source line's
prompt, when necessary.

Otherwise, if point is at the first non-whitespace character
following an unindented source line's prompt, then remove the
prompt (converting the line to an output line or text line).

Otherwise, if point is at the first non-whitespace character of a
line, the delete the line's indentation.

Otherwise, delete the preceeding character.
"
  (interactive "*")
  (cond 
   ;; Beginning of line: delete preceeding newline.
   ((bolp) (backward-delete-char 1))
      
   ;; First non-ws char following prompt: dedent or remove prompt.
   ((and (looking-at "[^ \t\n]\\|$") (doctest-looking-back doctest-prompt-re))
    (let* ((prompt-beg (match-beginning 2))
	   (indent-beg (match-beginning 3)) (indent-end (match-end 3))
	   (old-indent (- indent-end indent-beg))
	   (new-indent (* (/ (- old-indent 1) 4) 4)))
      (cond
       ;; Indented source line: dedent it.
       ((> old-indent 0)
	(goto-char indent-beg)
	(delete-region indent-beg indent-end)
	(insert-char ?\  new-indent)
	;; Change prompt to PS1, when appropriate.
	(when (and (= new-indent 0) (not (looking-at doctest-outdent-re)))
	  (delete-backward-char 4)
	  (insert-string ">>> ")))
       ;; Non-indented source line: remove prompt.
       (t
	(goto-char indent-end)
	(delete-region prompt-beg indent-end)))))

   ;; First non-ws char of a line: delete all indentation.
   ((and (looking-at "[^ \n\t]\\|$") (doctest-looking-back "^[ \t]+"))
    (delete-region (match-beginning 0) (match-end 0)))

   ;; Otherwise: delete a character.
   (t
    (backward-delete-char 1))))

(defun doctest-newline-and-indent ()
  "Insert a newline, and indent the new line appropriately.

If the current line is a source line containing a bare prompt,
then clear the current line, and insert a newline.

Otherwise, if the current line is a source line, then insert a
newline, and add an appropriately indented prompt to the new
line.

Otherwise, if the current line is an output line, then insert a
newline and indent the new line to match the example's margin.

Otherwise, insert a newline.

If `doctest-avoid-trailing-whitespace' is true, then clear any
whitespace to the left of the point before inserting a newline.
"
  (interactive "*")
  ;; If we're avoiding trailing spaces, then delete WS before point.
  (if doctest-avoid-trailing-whitespace
      (delete-char (- (skip-chars-backward " \t"))))     
  (cond 
   ;; If we're on an empty prompt, delete it.
   ((on-empty-doctest-source-line)
    (delete-region (match-beginning 0) (match-end 0))
    (insert-char ?\n 1))
   ;; If we're on a doctest line, add a new prompt.
   ((on-doctest-source-line)
    (insert-char ?\n 1)
    (doctest-indent-source-line))
   ;; If we're in doctest output, indent to the margin.
   ((on-doctest-output-line)
    (insert-char ?\n 1)
    (insert-char ?\  (doctest-current-source-line-margin)))
   ;; Otherwise, just add a newline.
   (t (insert-char ?\n 1))))

(defun doctest-electric-colon ()
  "Insert a colon, and dedent the line when appropriate."
  (interactive "*")
  (insert-char ?: 1)
  (when (on-doctest-source-line)
    (doctest-indent-source-line t)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Code Execution
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defun doctest-execute-buffer (&optional diff)
  "Run doctest on the current buffer, and display the results in the 
*doctest-output* buffer."
  (interactive "*")
  (setq doctest-results-buffer (get-buffer-create doctest-results-buffer-name))
  (let* ((temp (concat (doctest-temp-name) ".py"))
	 (tempfile (expand-file-name temp doctest-temp-directory))
	 (cur-buf (current-buffer))
	 (in-buf (get-buffer-create "*doctest-input*"))
	 (beg (point-min)) (end (point-max))
         (flags (reduce (lambda (a b) (if (equal b "") a (concat a "|" b)))
                        doctest-optionflags))
	 (script (concat "from doctest import *\n"
			 "doc = open('" tempfile "').read()\n"
			 "test = DocTestParser().get_doctest("
			         "doc, {}, '" (buffer-name) "', '"
				 (buffer-file-name) "', 0)\n"
                         "r = DocTestRunner(optionflags=" flags
                               (if diff "+REPORT_UDIFF" "")
                               ")\n"
			 "r.run(test)\n"
                         "print\n" ;; <- so the buffer won't be empty
                         ))
	 (cmd (concat doctest-python-command " -c \"" script "\"")))
    ;; Write buffer to a file.
    (save-excursion
      (set-buffer in-buf)
      (insert-buffer-substring cur-buf beg end)
      (write-file tempfile))
    ;; Run doctest
    (shell-command cmd doctest-results-buffer)
    ;; Delete the temp file
    (delete-file tempfile)
    ;; Delete the input buffer.
    (if (buffer-live-p in-buf)
        (kill-buffer in-buf))
    ;; Set mode on output buffer.
    (save-excursion
      (set-buffer doctest-results-buffer)
      (doctest-results-mode))
    ;; If any tests failed, display them.
    (cond ((> (buffer-size doctest-results-buffer) 1)
	   (display-buffer doctest-results-buffer)
	   (doctest-postprocess-results)
	   (message "Test failed!"))
	  (t
	   (display-buffer doctest-results-buffer)
           (if (get-buffer-window doctest-results-buffer)
	       (delete-window (get-buffer-window doctest-results-buffer)))
	   (message "Test passed!")
           ))))

(defun doctest-execute-buffer-with-diff ()
  "Run doctest on the current buffer, and display the results in the 
*doctest-output* buffer, using the diff format."
  (interactive "*")
  (doctest-execute-buffer t))

(defun doctest-postprocess-results ()
  (doctest-next-failure 1)
  (if hide-example-source
    (hide-example-source)))

(defun doctest-next-failure (count)
  "Move to the top of the next failing example, and highlight the
example's failure description in *doctest-output*."
  (interactive "p")
  (let (lineno)
    (cond
     ((not (buffer-live-p doctest-results-buffer))
      (message "Run doctest first! (C-c C-c)"))
     (t
      (let ((orig-window (selected-window))
            (results-window (display-buffer doctest-results-buffer)))
        (save-excursion
          (set-buffer doctest-results-buffer)
          ;; Switch to the results window (so its point gets updated)
          (if results-window (select-window results-window))
          ;; Pick up where we left off.
          ;; (nb: doctest-selected-failure is buffer-local)
          (goto-char (or doctest-selected-failure (point-min)))
          ;; Skip past anything on *this* line.
          (if (>= count 0) (end-of-line) (beginning-of-line))
          ;; Look for the next failure
          (if (>= count 0)
              (re-search-forward doctest-results-loc-re nil t count)
            (re-search-backward doctest-results-loc-re nil t (- count)))
          (cond
           ;; We found a failure:
           ((match-string 2)
            (let ((old-selected-failure doctest-selected-failure))
              ;; Extract the line number for the doctest file.
              (setq lineno (string-to-int (match-string 2)))
              ;; Store our position for next time.
              (beginning-of-line)
              (setq doctest-selected-failure (point))
              ;; Update selection.
              (doctest-fontify-line old-selected-failure)
              (doctest-fontify-line doctest-selected-failure)))
           ;; We didn't find a failure:
           (t
            (message "No failures found!"))))
          ;; Return to the original window
          (select-window orig-window))))

    (when lineno
      ;; Move point to the selected failure.
      (goto-line lineno)
;      ;; Highlight it. [XX] Under construction.
;      (let ((beg (save-excursion (beginning-of-line) (point)))
;            (end (save-excursion (end-of-line) (point))))
;        (add-text-properties (point-min) (point-max) '(doctest-selected nil))
;        (add-text-properties beg end '(doctest-selected t))
;        (doctest-fontify-line (point)))
      )))

(defun doctest-prev-failure (count)
  "Move to the top of the previous failing example, and highlight
the example's failure description in *doctest-output*."
  (interactive "p")
  (doctest-next-failure (- count)))

(defun doctest-first-failure ()
  (interactive "")
  (if (buffer-live-p doctest-results-buffer)
      (save-excursion
        (set-buffer doctest-results-buffer)
        (let ((old-selected-failure doctest-selected-failure))
          (setq doctest-selected-failure (point-min))
          (doctest-fontify-line old-selected-failure))))
  (doctest-next-failure 1))

(defun doctest-last-failure ()
  (interactive "")
  (if (buffer-live-p doctest-results-buffer)
      (save-excursion
        (set-buffer doctest-results-buffer)
        (let ((old-selected-failure doctest-selected-failure))
          (setq doctest-selected-failure (point-max))
          (doctest-fontify-line old-selected-failure))))
  (doctest-next-failure -1))

(defconst doctest-example-source-re 
  "^Failed example:\n\\(\n\\|    [^\n]*\n\\)+")
(defun hide-example-source ()
  "Delete the source code listings from the results buffer (since it's
easy enough to see them in the original buffer)"
  (save-excursion
    (set-buffer doctest-results-buffer)
    (toggle-read-only nil)
    (beginning-of-buffer)
    (while (re-search-forward doctest-example-source-re nil t)
      (replace-match "" nil nil))
    (toggle-read-only t)))


;; Unfortunately, the `replace-regexp-in-string' is not provided by all
;; versions of Emacs.  But this will do the job:
(defun doctest-replace-regexp-in-string (regexp replacement text)
  "Return the result of replacing all mtaches of REGEXP with
REPLACEMENT in TEXT.  (Since replace-regexp-in-string is not available
under all versions of emacs, and is called different names in
different versions, this compatibility function will emulate it if
it's not available."
  (let ((start 0) (repl-len (length replacement)))
    (while (string-match regexp text start)
      (setq start (+ (match-beginning 0) repl-len 1))
      (setq text (replace-match replacement t nil text)))
    text))

(defun doctest-results-next-header ()
  (if (re-search-forward (concat doctest-results-header-re "\\|"
                                 doctest-results-divider-re) nil t)
      (let ((result (match-string 0)))
        (if (string-match doctest-results-header-re result)
            result
          nil))
    nil))
          
(defun doctest-replace-output ()
  "Move to the top of the closest example, and replace its output
with the 'got' output from the *doctest-output* buffer.  An error is
displayed if the chosen example is not listed in *doctest-output*, or
if the 'expected' output for the example does not exactly match the
output listed in the source buffer.  The user is asked to confirm the
replacement."
  (interactive)
  ;; Move to the beginning of the example.
  (cond
   ((not (buffer-live-p doctest-results-buffer))
    (message "Run doctest first! (C-c C-c)"))
   (t
    (save-excursion
      (let ((orig-buffer (current-buffer)))
        ;; Find the doctest case closest to the cursor.
        (end-of-line)
        (re-search-backward "^\\( *\\)>>> " nil t)
        ;; Find the corresponding doctest in the output buffer.
        (let ((prompt-indent (match-string 1))
              (output-re (format "^File .*, line %d," (line-number)))
              (doctest-got nil) (doctest-expected nil) (header nil))
          (set-buffer doctest-results-buffer)

          ;; Find the corresponding example in the output.
          (goto-char (point-min))
          (if (not (re-search-forward output-re nil t))
              (error "Could not find corresponding output"))

          ;; Get the output's 'expected' & 'got' texts.
          (while (setq header (doctest-results-next-header))
            (cond
             ((equal header "Failed example:")
              t)
             ((equal header "Expected nothing")
              (setq doctest-expected ""))
             ((equal header "Expected:")
              (re-search-forward "^\\(\\(    \\).*\n\\)*")
              (setq doctest-expected (doctest-replace-regexp-in-string
                                 "^    " prompt-indent (match-string 0))))
             ((equal header "Got nothing")
              (setq doctest-got ""))
             ((or (equal header "Got:") (equal header "Exception raised:"))
              (re-search-forward "^\\(\\(    \\).*\n\\)*")
              (setq doctest-got (doctest-replace-regexp-in-string
                                 "^    " prompt-indent (match-string 0))))
             (t (error "Unexpected header %s" header))))

          ;; Go back to the source buffer.
          (set-buffer orig-buffer)
          
          ;; Skip ahead to the output.
          (re-search-forward "^ *>>>.*\n\\( *\\.\\.\\..*\n\\)*")
          
          ;; Check that the output matches.
          (let ((start (point)) end)
            (re-search-forward "^ *\\(>>>.*\\|$\\)")
            (setq end (match-beginning 0))
            (if doctest-expected
                (if (not (equal (buffer-substring start end) doctest-expected))
                    (error "Output does mot match 'expected'")))
            (setq doctest-expected (buffer-substring start end))
            (goto-char end))

          (let ((confirm-buffer (get-buffer-create "*doctest-confirm*")))
            (set-buffer confirm-buffer)
            ;; Erase anything left over in the buffer.
            (delete-region (point-min) (point-max))
            ;; Write a confirmation message
            (if (equal doctest-expected "")
                (insert-string "Replace nothing\n")
              (insert-string (concat "Replace:\n" doctest-expected)))
            (if (equal doctest-got "")
                (insert-string "With nothing\n")
              (insert-string (concat "With:\n" doctest-got)))
            (let ((confirm-window (display-buffer confirm-buffer nil nil t)))
              ;; Get confirmation
              (set-buffer orig-buffer)
              ;; [XX]
              (if doctest-expected
                  (search-backward doctest-expected)
                t)
              (when (y-or-n-p "Ok to replace? ")
                (replace-match doctest-got t t))
              (kill-buffer confirm-buffer)
              (delete-window confirm-window)))))))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Doctest Results Mode (output of doctest-execute-buffer)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; [XX] Todo:
;;   - Make it read-only?
;;   - Hitting enter goes to the corresponding error
;;   - Clicking goes to corresponding error (not as useful)


(defconst doctest-results-divider-re
  "^\\([*]\\{60,\\}\\)$")

(defconst doctest-results-loc-re
  "^File \"\\([^\"]+\\)\", line \\([0-9]+\\), in \\([^\n]+\\)")

(defconst doctest-results-header-re
  "^\\([a-zA-Z0-9 ]+:\\|Expected nothing\\|Got nothing\\)$")

(defconst doctest-results-font-lock-keywords
  `((,doctest-results-divider-re 
     (0 'doctest-results-divider-face))
    (,doctest-results-loc-re 
     (0 'doctest-results-loc-face))
    (,doctest-results-header-re 
     (0 'doctest-results-header-face))
    (doctest-results-selection-matcher 
     (0 'doctest-results-selection-face t))))

(defun doctest-results-selection-matcher (limit)
  "Matches from `doctest-selected-failure' to the end of the
line.  This is used to highlight the currently selected failure."
  (when (and doctest-selected-failure
	     (<= (point) doctest-selected-failure)
	     (< doctest-selected-failure limit))
    (goto-char doctest-selected-failure)
    (search-forward-regexp "[^\n]+" limit)))

;; Register the font-lock keywords (xemacs)
(put 'doctest-results-mode 'font-lock-defaults 
     '(doctest-results-font-lock-keywords))

;; Register the font-lock keywords (gnu emacs)
(defvar font-lock-defaults-alist nil) ; in case we're in xemacs
(setq font-lock-defaults-alist
      (append font-lock-defaults-alist
              `((doctest-results-mode 
		 doctest-results-font-lock-keywords 
		 nil nil nil nil))))

;; Define the mode
(define-derived-mode doctest-results-mode text-mode "Doctest Results"
  "docstring"
  ;; Enable font-lock mode.
  (if (featurep 'font-lock) (font-lock-mode 1))
  ;; Keep track of which failure is selected
  (set (make-local-variable 'doctest-selected-failure) nil)
  ;; Make the buffer read-only.
  (toggle-read-only t))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Helper functions
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defun on-doctest-source-line ()
  "Return true if the current line is a source line."
  (save-excursion
    (beginning-of-line)
    (looking-at doctest-prompt-re)))

(defun on-empty-doctest-source-line ()
  "Return true if the current line contains a bare prompt."
  (save-excursion
    (beginning-of-line)
    (looking-at (concat doctest-prompt-re "$"))))

(defun on-doctest-output-line ()
  "Return true if the current line is an output line."
  (save-excursion
    (beginning-of-line)
    (let ((prompt-or-blankline (concat doctest-prompt-re "\\|" "^[ \t]*\n")))
      ;; The line must not be blank or start with a prompt.
      (when (not (looking-at prompt-or-blankline))
          ;; The line must follow a line starting with a prompt, with
          ;; no intervening blank lines.
          (search-backward-regexp prompt-or-blankline nil t)
          (looking-at doctest-prompt-re)))))

(defun find-doctest-output-line (&optional limit)
  "Move forward to the next doctest output line (staying within
the given bounds).  Return the character position of the doctest
output line if one was found, and false otherwise."
  (let ((found-it nil) ; point where we found an output line
	(limit (or limit (point-max)))) ; default value for limit
    (save-excursion
      ;; Keep moving forward, one line at a time, until we find a
      ;; doctest output line.
      (while (and (not found-it) (< (point) limit) (not (eobp)))
	(if (and (not (eolp)) (on-doctest-output-line))
	    (setq found-it (point))
	  (forward-line))))
    ;; If we found a doctest output line, then go to it.
    (if found-it (goto-char found-it))))

(defun doctest-version ()
  "Echo the current version of `doctest-mode' in the minibuffer."
  (interactive)
  (message "Using `doctest-mode' version %s" doctest-version))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Utility functions
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defvar doctest-serial-number 0) ;used if broken-temp-names.
(defun doctest-temp-name ()
  (if (memq 'broken-temp-names features)
      (let
	  ((sn doctest-serial-number)
	   (pid (and (fboundp 'emacs-pid) (emacs-pid))))
	(setq doctest-serial-number (1+ doctest-serial-number))
	(if pid
	    (format "doctest-%d-%d" sn pid)
	  (format "doctest-%d" sn)))
    (make-temp-name "doctest-")))

(defun column-at-char (pos)
  "Return the column of the given character position"
  (save-excursion (goto-char pos) (current-column)))

(defun doctest-looking-back (regexp)
  "Return True if the text before point matches the given regular
expression.  Like looking-at except backwards and slower.  (This
is available as `looking-back' in GNU emacs and
`looking-at-backwards' in XEmacs, but it's easy enough to define
from scratch such that it works under both.)"
  (save-excursion
    (let ((orig-pos (point)))
      ;; Search backwards for the regexp.
      (if (re-search-backward regexp nil t)
	  ;; Check if it ends at the original point.
	  (= orig-pos (match-end 0))))))

(defun doctest-fontify-line (charpos)
  "Run font-lock-fontify-region on the line containing the given
position."
  (if charpos
      (save-excursion
        (goto-char charpos)
        (let ((beg (progn (beginning-of-line) (point)))
              (end (progn (end-of-line) (point))))
          (font-lock-fontify-region beg end)))))
  
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Syntax Table
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; We do *NOT* currently use this, because it applies too
;; indiscrimanantly.  In particular, we don't want "'" and '"' treated
;; as quote marks on text lines.  But there's no good way to prevent
;; it.
(defvar doctest-syntax-alist nil
  "Syntax alist used in `doctest-mode' buffers.")
(setq doctest-syntax-alist '((?\( . "()") (?\[ . "(]") (?\{ . "(}")
			     (?\) . ")(") (?\] . ")[") (?\} . "){")
			     (?\$ . "." ) (?\% . "." ) (?\& . "." )
			     (?\* . "." ) (?\+ . "." ) (?\- . "." )
			     (?\/ . "." ) (?\< . "." ) (?\= . "." )
			     (?\> . "." ) (?\| . "." ) (?\_ . "w" )
			     (?\' . "\"") (?\" . "\"") (?\` . "$" )
			     (?\# . "<" ) (?\n . ">" )))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Key Bindings
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defconst doctest-mode-map 
  (let ((map (make-keymap)))
    (define-key map [backspace] 'doctest-electric-backspace)
    (define-key map [return] 'doctest-newline-and-indent)
    (define-key map [tab] 'doctest-indent-source-line)
    (define-key map ":" 'doctest-electric-colon)
    (define-key map "\C-c\C-v" 'doctest-version)
    (define-key map "\C-c\C-c" 'doctest-execute-buffer)
    (define-key map "\C-c\C-d" 'doctest-execute-buffer-with-diff)
    (define-key map "\C-c\C-n" 'doctest-next-failure)
    (define-key map "\C-c\C-p" 'doctest-prev-failure)
    (define-key map "\C-c\C-a" 'doctest-first-failure)
    (define-key map "\C-c\C-z" 'doctest-last-failure)
    (define-key map "\C-c\C-r" 'doctest-replace-output)
    map) 
  "Keymap for doctest-mode.")

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Define the mode
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Register the font-lock keywords (xemacs)
(put 'doctest-mode 'font-lock-defaults '(doctest-font-lock-keywords))

;; Register the font-lock keywords (gnu emacs)
(defvar font-lock-defaults-alist nil) ; in case we're in xemacs
(setq font-lock-defaults-alist
      (append font-lock-defaults-alist
              `((doctest-mode doctest-font-lock-keywords nil nil nil nil))))

(defvar doctest-results-buffer nil
  "The output buffer for doctest-mode")

;; Use doctest mode for files ending in .doctest
;;;###autoload
(add-to-list 'auto-mode-alist '("\\.doctest$" . doctest-mode))

;;;###autoload
(define-derived-mode doctest-mode text-mode "Doctest"
  "A major mode for editing text files that contain Python
doctest examples.  Doctest is a testing framework for Python that
emulates an interactive session, and checks the result of each
command.  For more information, see the Python library reference:
<http://docs.python.org/lib/module-doctest.html>

`doctest-mode' defines three kinds of line, each of which is
treated differently:

  - 'Source lines' are lines consisting of a Python prompt
    ('>>>' or '...'), followed by source code.  Source lines are
    colored (similarly to `python-mode') and auto-indented.

  - 'Output lines' are non-blank lines immediately following
    source lines.  They are colored using several doctest-
    specific output faces.

  - 'Text lines' are any other lines.  They are not processed in
    any special way.

\\{doctest-mode-map}
"
  ;; Enable auto-fill mode.
  (auto-fill-mode 1)

  ;; Enable font-lock mode.
  (if (featurep 'font-lock) (font-lock-mode 1))
  
  ;; Register our indentation function.
  (set (make-local-variable 'indent-line-function) 
       'doctest-indent-source-line)

  ;; Keep track of our results buffer.
  (set (make-local-variable 'doctest-results-buffer) nil)
  )

(provide 'doctest-mode)
;;; doctest-mode.el ends here
