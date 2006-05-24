;;; rst-mode.el --- Mode for viewing and editing reStructuredText-documents.

;; Copyright 2003 Stefan Merten <smerten@oekonux.de>
;; 
;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation; either version 2 of the License, or
;; (at your option) any later version.
;; 
;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.
;; 
;; You should have received a copy of the GNU General Public License
;; along with this program; if not, write to the Free Software
;; Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

;;; Commentary:

;; This package provides support for documents marked up using the
;; reStructuredText format
;; [http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html].
;; Support includes font locking as well as some convenience functions
;; for editing.

;; The package is based on `text-mode' and inherits some things from it.
;; Particularly `text-mode-hook' is run before `rst-mode-hook'.

;; Add the following lines to your `.emacs' file:
;;
;; (autoload 'rst-mode "rst-mode" "mode for editing reStructuredText documents" t)
;; (setq auto-mode-alist
;;       (append '(("\\.rst$" . rst-mode)
;;                 ("\\.rest$" . rst-mode)) auto-mode-alist))
;;
;; If you are using `.txt' as a standard extension for reST files as
;; http://docutils.sourceforge.net/FAQ.html#what-s-the-standard-filename-extension-for-a-restructuredtext-file
;; suggests you may use one of the `Local Variables in Files' mechanism Emacs
;; provides to set the major mode automatically. For instance you may use
;;
;; .. -*- mode: rst -*-
;;
;; in the very first line of your file. However, because this is a major
;; security breach you or your administrator may have chosen to switch that
;; feature off. See `Local Variables in Files' in the Emacs documentation for a
;; more complete discussion.

;;; Code:

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;;; Customization:

(defgroup rst nil "Support for reStructuredText documents"
  :group 'wp
  :version "21.1"
  :link '(url-link "http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html"))

(defcustom rst-mode-hook nil
  "Hook run when Rst Mode is turned on. The hook for Text Mode is run before
  this one."
  :group 'rst
  :type '(hook))

(defcustom rst-mode-lazy t
  "*If non-nil Rst Mode font-locks comment, literal blocks, and section titles
correctly. Because this is really slow it switches on Lazy Lock Mode
automatically. You may increase Lazy Lock Defer Time for reasonable results.

If nil comments and literal blocks are font-locked only on the line they start.

The value of this variable is used when Rst Mode is turned on."
  :group 'rst
  :type '(boolean))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defgroup rst-faces nil "Faces used in Rst Mode"
  :group 'rst
  :group 'faces
  :version "21.1")

(defcustom rst-block-face 'font-lock-keyword-face
  "All syntax marking up a special block"
  :group 'rst-faces
  :type '(face))

(defcustom rst-external-face 'font-lock-type-face
  "Field names and interpreted text"
  :group 'rst-faces
  :type '(face))

(defcustom rst-definition-face 'font-lock-function-name-face
  "All other defining constructs"
  :group 'rst-faces
  :type '(face))

(defcustom rst-directive-face
  ;; XEmacs compatibility
  (if (boundp 'font-lock-builtin-face)
      'font-lock-builtin-face
    'font-lock-preprocessor-face)
  "Directives and roles"
  :group 'rst-faces
  :type '(face))

(defcustom rst-comment-face 'font-lock-comment-face
  "Comments"
  :group 'rst-faces
  :type '(face))

(defcustom rst-emphasis1-face
  ;; XEmacs compatibility
  (if (facep 'italic)
      ''italic
    'italic)
  "Simple emphasis"
  :group 'rst-faces
  :type '(face))

(defcustom rst-emphasis2-face
  ;; XEmacs compatibility
  (if (facep 'bold)
      ''bold
    'bold)
  "Double emphasis"
  :group 'rst-faces
  :type '(face))

(defcustom rst-literal-face 'font-lock-string-face
  "Literal text"
  :group 'rst-faces
  :type '(face))

(defcustom rst-reference-face 'font-lock-variable-name-face
  "References to a definition"
  :group 'rst-faces
  :type '(face))

;; Faces for displaying items on several levels; these definitions define
;; different shades of grey where the lightest one is used for level 1
(defconst rst-level-face-max 6
  "Maximum depth of level faces defined")
(defconst rst-level-face-base-color "grey"
  "The base color to be used for creating level faces")
(defconst rst-level-face-base-light 85
  "The lightness factor for the base color")
(defconst rst-level-face-format-light "%2d"
  "The format for the lightness factor for the base color")
(defconst rst-level-face-step-light -7
  "The step width to use for next color")

;; Define the faces
(let ((i 1))
  (while (<= i rst-level-face-max)
    (let ((sym (intern (format "rst-level-%d-face" i)))
	  (doc (format "Face for showing section title text at level %d" i))
	  (col (format (concat "%s" rst-level-face-format-light)
		       rst-level-face-base-color
		       (+ (* (1- i) rst-level-face-step-light)
			  rst-level-face-base-light))))
      (make-empty-face sym)
      (set-face-doc-string sym doc)
      (set-face-background sym col)
      (set sym sym)
    (setq i (1+ i)))))

(defcustom rst-adornment-faces-alist
  '((1 . rst-level-1-face)
    (2 . rst-level-2-face)
    (3 . rst-level-3-face)
    (4 . rst-level-4-face)
    (5 . rst-level-5-face)
    (6 . rst-level-6-face)
    (t . font-lock-keyword-face)
    (nil . font-lock-keyword-face))
  "Provides faces for the various adornment types. Key is a number (for the
section title text of that level), t (for transitions) or nil (for section
title adornment)."
  :group 'rst-faces
  :type '(alist :key-type (choice (integer :tag "Section level")
				  (boolean :tag "transitions (on) / section title adornment (off)"))
		:value-type (face)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; FIXME: Code from `restructuredtext.el' should be integrated

(defvar rst-mode-syntax-table nil
  "Syntax table used while in rst mode.")

(unless rst-mode-syntax-table
  (setq rst-mode-syntax-table (make-syntax-table text-mode-syntax-table))
  (modify-syntax-entry ?$ "." rst-mode-syntax-table)
  (modify-syntax-entry ?% "." rst-mode-syntax-table)
  (modify-syntax-entry ?& "." rst-mode-syntax-table)
  (modify-syntax-entry ?' "." rst-mode-syntax-table)
  (modify-syntax-entry ?* "." rst-mode-syntax-table)
  (modify-syntax-entry ?+ "." rst-mode-syntax-table)
  (modify-syntax-entry ?. "_" rst-mode-syntax-table)
  (modify-syntax-entry ?/ "." rst-mode-syntax-table)
  (modify-syntax-entry ?< "." rst-mode-syntax-table)
  (modify-syntax-entry ?= "." rst-mode-syntax-table)
  (modify-syntax-entry ?> "." rst-mode-syntax-table)
  (modify-syntax-entry ?\\ "\\" rst-mode-syntax-table)
  (modify-syntax-entry ?| "." rst-mode-syntax-table)
  (modify-syntax-entry ?_ "." rst-mode-syntax-table)
  )

(defvar rst-mode-abbrev-table nil
 "Abbrev table used while in rst mode.")
(define-abbrev-table 'rst-mode-abbrev-table ())

;; FIXME: Movement keys to skip forward / backward over or mark an indented
;; block could be defined; keys to markup section titles based on
;; `rst-adornment-level-alist' would be useful
(defvar rst-mode-map nil
  "Keymap for rst mode. This inherits from Text mode.")

(unless rst-mode-map
  (setq rst-mode-map (copy-keymap text-mode-map)))

(defun rst-mode ()
  "Major mode for editing reStructuredText documents.

You may customize `rst-mode-lazy' to switch font-locking of blocks.

\\{rst-mode-map}
Turning on `rst-mode' calls the normal hooks `text-mode-hook' and
`rst-mode-hook'."
  (interactive)
  (kill-all-local-variables)

  ;; Maps and tables
  (use-local-map rst-mode-map)
  (setq local-abbrev-table rst-mode-abbrev-table)
  (set-syntax-table rst-mode-syntax-table)

  ;; For editing text
  ;;
  ;; FIXME: It would be better if this matches more exactly the start of a reST
  ;; paragraph; however, this not always possible with a simple regex because
  ;; paragraphs are determined by indentation of the following line
  (set (make-local-variable 'paragraph-start)
       (concat page-delimiter "\\|[ \t]*$"))
  (if (eq ?^ (aref paragraph-start 0))
      (setq paragraph-start (substring paragraph-start 1)))
  (set (make-local-variable 'paragraph-separate) paragraph-start)
  (set (make-local-variable 'indent-line-function) 'indent-relative-maybe)
  (set (make-local-variable 'adaptive-fill-mode) t)
  (set (make-local-variable 'comment-start) ".. ")

  ;; Special variables
  (make-local-variable 'rst-adornment-level-alist)

  ;; Font lock
  (set (make-local-variable 'font-lock-defaults)
       '(rst-font-lock-keywords-function
	 t nil nil nil
	 (font-lock-multiline . t)
	 (font-lock-mark-block-function . mark-paragraph)))
  (when (boundp 'font-lock-support-mode)
    ;; rst-mode has its own mind about font-lock-support-mode
    (make-local-variable 'font-lock-support-mode)
    (cond
     ((and (not rst-mode-lazy) (not font-lock-support-mode)))
     ;; No support mode set and none required - leave it alone
     ((or (not font-lock-support-mode) ;; No support mode set (but required)
	  (symbolp font-lock-support-mode)) ;; or a fixed mode for all
      (setq font-lock-support-mode
	    (list (cons 'rst-mode (and rst-mode-lazy 'lazy-lock-mode))
		  (cons t font-lock-support-mode))))
     ((and (listp font-lock-support-mode)
	   (not (assoc 'rst-mode font-lock-support-mode)))
      ;; A list of modes missing rst-mode
      (setq font-lock-support-mode
	    (append '((cons 'rst-mode (and rst-mode-lazy 'lazy-lock-mode)))
		    font-lock-support-mode)))))

  ;; Names and hooks
  (setq mode-name "reST")
  (setq major-mode 'rst-mode)
  (run-hooks 'text-mode-hook)
  (run-hooks 'rst-mode-hook))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Font lock

(defun rst-font-lock-keywords-function ()
  "Returns keywords to highlight in rst mode according to current settings."
  ;; The reST-links in the comments below all relate to sections in
  ;; http://docutils.sourceforge.net/docs/ref/rst/restructuredtext.html
  (let* ( ;; This gets big - so let's define some abbreviations
	 ;; horizontal white space
	 (re-hws "[\t ]")
	 ;; beginning of line with possible indentation
	 (re-bol (concat "^" re-hws "*"))
	 ;; Separates block lead-ins from their content
	 (re-blksep1 (concat "\\(" re-hws "+\\|$\\)"))
	 ;; explicit markup tag
	 (re-emt "\\.\\.")
	 ;; explicit markup start
	 (re-ems (concat re-emt re-hws "+"))
	 ;; inline markup prefix
	 (re-imp1 (concat "\\(^\\|" re-hws "\\|[-'\"([{</:]\\)"))
	 ;; inline markup suffix
	 (re-ims1 (concat "\\(" re-hws "\\|[]-'\")}>/:.,;!?\\]\\|$\\)"))
	 ;; symbol character
	 (re-sym1 "\\(\\sw\\|\\s_\\)")
	 ;; inline markup content begin
	 (re-imbeg2 "\\(\\S \\|\\S \\([^")

	 ;; There seems to be a bug leading to error "Stack overflow in regexp
	 ;; matcher" when "|" or "\\*" are the characters searched for
	 (re-imendbeg
	  (if (< emacs-major-version 21)
	      "]"
	    "\\]\\|\\\\."))
	 ;; inline markup content end
	 (re-imend (concat re-imendbeg "\\)*[^\t \\\\]\\)"))
	 ;; inline markup content without asterisk
	 (re-ima2 (concat re-imbeg2 "*" re-imend))
	 ;; inline markup content without backquote
	 (re-imb2 (concat re-imbeg2 "`" re-imend))
	 ;; inline markup content without vertical bar
	 (re-imv2 (concat re-imbeg2 "|" re-imend))
	 ;; Supported URI schemes
	 (re-uris1 "\\(acap\\|cid\\|data\\|dav\\|fax\\|file\\|ftp\\|gopher\\|http\\|https\\|imap\\|ldap\\|mailto\\|mid\\|modem\\|news\\|nfs\\|nntp\\|pop\\|prospero\\|rtsp\\|service\\|sip\\|tel\\|telnet\\|tip\\|urn\\|vemmi\\|wais\\)")
	 ;; Line starting with adornment and optional whitespace; complete
	 ;; adornment is in (match-string 1); there must be at least 3
	 ;; characters because otherwise explicit markup start would be
	 ;; recognized
	 (re-ado2 (concat "^\\(\\(["
			  (if (or
			       (< emacs-major-version 21)
			       (save-match-data
				 (string-match "XEmacs\\|Lucid" emacs-version)))
			      "^a-zA-Z0-9 \t\x00-\x1F"
			    "^[:word:][:space:][:cntrl:]")
			  "]\\)\\2\\2+\\)" re-hws "*$"))
	 )
    (list
     ;; FIXME: Block markup is not recognized in blocks after explicit markup
     ;; start

     ;; Simple `Body Elements`_
     ;; `Bullet Lists`_
     (list
      (concat re-bol "\\([-*+]" re-blksep1 "\\)")
      1 rst-block-face)
     ;; `Enumerated Lists`_
     (list
      (concat re-bol "\\((?\\([0-9]+\\|[A-Za-z]\\|[IVXLCMivxlcm]+\\)[.)]" re-blksep1 "\\)")
      1 rst-block-face)
     ;; `Definition Lists`_ FIXME: missing
     ;; `Field Lists`_
     (list
      (concat re-bol "\\(:[^:]+:\\)" re-blksep1)
      1 rst-external-face)
     ;; `Option Lists`_
     (list
      (concat re-bol "\\(\\(\\(\\([-+/]\\|--\\)\\sw\\(-\\|\\sw\\)*\\([ =]\\S +\\)?\\)\\(,[\t ]\\)?\\)+\\)\\($\\|[\t ]\\{2\\}\\)")
      1 rst-block-face)

     ;; `Tables`_ FIXME: missing

     ;; All the `Explicit Markup Blocks`_
     ;; `Footnotes`_ / `Citations`_
     (list
      (concat re-bol "\\(" re-ems "\\[[^[]+\\]\\)" re-blksep1)
      1 rst-definition-face)
     ;; `Directives`_ / `Substitution Definitions`_
     (list
      (concat re-bol "\\(" re-ems "\\)\\(\\(|[^|]+|[\t ]+\\)?\\)\\(" re-sym1 "+::\\)" re-blksep1)
      (list 1 rst-directive-face)
      (list 2 rst-definition-face)
      (list 4 rst-directive-face))
     ;; `Hyperlink Targets`_
     (list
      (concat re-bol "\\(" re-ems "_\\([^:\\`]\\|\\\\.\\|`[^`]+`\\)+:\\)" re-blksep1)
      1 rst-definition-face)
     (list
      (concat re-bol "\\(__\\)" re-blksep1)
      1 rst-definition-face)

     ;; All `Inline Markup`_
     ;; FIXME: Condition 5 preventing fontification of e.g. "*" not implemented
     ;; `Strong Emphasis`_
     (list
      (concat re-imp1 "\\(\\*\\*" re-ima2 "\\*\\*\\)" re-ims1)
      2 rst-emphasis2-face)
     ;; `Emphasis`_
     (list
      (concat re-imp1 "\\(\\*" re-ima2 "\\*\\)" re-ims1)
      2 rst-emphasis1-face)
     ;; `Inline Literals`_
     (list
      (concat re-imp1 "\\(``" re-imb2 "``\\)" re-ims1)
      2 rst-literal-face)
     ;; `Inline Internal Targets`_
     (list
      (concat re-imp1 "\\(_`" re-imb2 "`\\)" re-ims1)
      2 rst-definition-face)
     ;; `Hyperlink References`_
     ;; FIXME: `Embedded URIs`_ not considered
     (list
      (concat re-imp1 "\\(\\(`" re-imb2 "`\\|\\sw+\\)__?\\)" re-ims1)
      2 rst-reference-face)
     ;; `Interpreted Text`_
     (list
      (concat re-imp1 "\\(\\(:" re-sym1 "+:\\)?\\)\\(`" re-imb2 "`\\)\\(\\(:" re-sym1 "+:\\)?\\)" re-ims1)
      (list 2 rst-directive-face)
      (list 5 rst-external-face)
      (list 8 rst-directive-face))
     ;; `Footnote References`_ / `Citation References`_
     (list
      (concat re-imp1 "\\(\\[[^]]+\\]_\\)" re-ims1)
      2 rst-reference-face)
     ;; `Substitution References`_
     (list
      (concat re-imp1 "\\(|" re-imv2 "|\\)" re-ims1)
      2 rst-reference-face)
     ;; `Standalone Hyperlinks`_
     (list
      ;; FIXME: This takes it easy by using a whitespace as delimiter
      (concat re-imp1 "\\(" re-uris1 ":\\S +\\)" re-ims1)
      2 rst-definition-face)
     (list
      (concat re-imp1 "\\(" re-sym1 "+@" re-sym1 "+\\)" re-ims1)
      2 rst-definition-face)

     ;; Do all block fontification as late as possible so 'append works

     ;; Sections_ / Transitions_
     (append
      (list
       re-ado2)
      (if (not rst-mode-lazy)
	  (list 1 rst-block-face)
	(list
	 (list 'rst-font-lock-handle-adornment
	       '(progn
		  (setq rst-font-lock-adornment-point (match-end 1))
		  (point-max))
	       nil
	       (list 1 '(cdr (assoc nil rst-adornment-faces-alist))
		     'append t)
	       (list 2 '(cdr (assoc rst-font-lock-level rst-adornment-faces-alist))
		     'append t)
	       (list 3 '(cdr (assoc nil rst-adornment-faces-alist))
		     'append t)))))

     ;; `Comments`_
     (append
      (list
       (concat re-bol "\\(" re-ems "\\)\[^[|_]\\([^:]\\|:\\([^:]\\|$\\)\\)*$")
       (list 1 rst-comment-face))
      (if rst-mode-lazy
	  (list
	   (list 'rst-font-lock-find-unindented-line
		 '(progn
		    (setq rst-font-lock-indentation-point (match-end 1))
		    (point-max))
		 nil
		 (list 0 rst-comment-face 'append)))))
     (append
      (list
       (concat re-bol "\\(" re-emt "\\)\\(\\s *\\)$")
       (list 1 rst-comment-face)
       (list 2 rst-comment-face))
      (if rst-mode-lazy
	  (list
	   (list 'rst-font-lock-find-unindented-line
		 '(progn
		    (setq rst-font-lock-indentation-point 'next)
		    (point-max))
		 nil
		 (list 0 rst-comment-face 'append)))))

     ;; `Literal Blocks`_
     (append
      (list
       (concat re-bol "\\(\\([^.\n]\\|\\.[^.\n]\\).*\\)?\\(::\\)$")
       (list 3 rst-block-face))
      (if rst-mode-lazy
	  (list
	   (list 'rst-font-lock-find-unindented-line
		 '(progn
		    (setq rst-font-lock-indentation-point t)
		    (point-max))
		 nil
		 (list 0 rst-literal-face 'append)))))
     )))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Indented blocks

(defun rst-forward-indented-block (&optional column limit)
  "Move forward across one indented block.
Find the next non-empty line which is not indented at least to COLUMN (defaults
to the column of the point). Moves point to first character of this line or the
first empty line immediately before it and returns that position. If there is
no such line before LIMIT (defaults to the end of the buffer) returns nil and
point is not moved."
  (interactive)
  (let ((clm (or column (current-column)))
	(start (point))
	fnd beg cand)
    (if (not limit)
	(setq limit (point-max)))
    (save-match-data
      (while (and (not fnd) (< (point) limit))
	(forward-line 1)
	(when (< (point) limit)
	  (setq beg (point))
	  (if (looking-at "\\s *$")
	      (setq cand (or cand beg)) ; An empty line is a candidate
	    (move-to-column clm)
	    ;; FIXME: No indentation [(zerop clm)] must be handled in some
	    ;; useful way - though it is not clear what this should mean at all
	    (if (string-match
		 "^\\s *$" (buffer-substring-no-properties beg (point)))
		(setq cand nil) ; An indented line resets a candidate
	      (setq fnd (or cand beg)))))))
    (goto-char (or fnd start))
    fnd))

;; Stores the point where the current indentation ends if a number. If `next'
;; indicates `rst-font-lock-find-unindented-line' shall take the indentation
;; from the next line if this is not empty. If non-nil indicates
;; `rst-font-lock-find-unindented-line' shall take the indentation from the
;; next non-empty line. Also used as a trigger for
;; `rst-font-lock-find-unindented-line'.
(defvar rst-font-lock-indentation-point nil)

(defun rst-font-lock-find-unindented-line (limit)
  (let* ((ind-pnt rst-font-lock-indentation-point)
	 (beg-pnt ind-pnt))
    ;; May run only once - enforce this
    (setq rst-font-lock-indentation-point nil)
    (when (and ind-pnt (not (numberp ind-pnt)))
      ;; Find indentation point in next line if any
      (setq ind-pnt
	    (save-excursion
	      (save-match-data
		(if (eq ind-pnt 'next)
		    (when (and (zerop (forward-line 1)) (< (point) limit))
		      (setq beg-pnt (point))
		      (when (not (looking-at "\\s *$"))
			(looking-at "\\s *")
			(match-end 0)))
		  (while (and (zerop (forward-line 1)) (< (point) limit)
			      (looking-at "\\s *$")))
		  (when (< (point) limit)
		    (setq beg-pnt (point))
		    (looking-at "\\s *")
		    (match-end 0)))))))
    (when ind-pnt
      (goto-char ind-pnt)
      ;; Always succeeds because the limit set by PRE-MATCH-FORM is the
      ;; ultimate point to find
      (goto-char (or (rst-forward-indented-block nil limit) limit))
      (set-match-data (list beg-pnt (point)))
      t)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Adornments

;; Stores the point where the current adornment ends. Also used as a trigger
;; for `rst-font-lock-handle-adornment'.
(defvar rst-font-lock-adornment-point nil)

;; Here `rst-font-lock-handle-adornment' stores the section level of the
;; current adornment or t for a transition.
(defvar rst-font-lock-level nil)

;; FIXME: It would be good if this could be used to markup section titles of
;; given level with a special key; it would be even better to be able to
;; customize this so it can be used for a generally available personal style
;;
;; FIXME: There should be some way to reset and reload this variable - probably
;; a special key
;;
;; FIXME: Some support for `outline-mode' would be nice which should be based
;; on this information
(defvar rst-adornment-level-alist nil
  "Associates adornments with section levels.
The key is a two character string. The first character is the adornment
character. The second character distinguishes underline section titles (`u')
from overline/underline section titles (`o'). The value is the section level.

This is made buffer local on start and adornments found during font lock are
entered.")

;; Returns section level for adornment key KEY. Adds new section level if KEY
;; is not found and ADD. If KEY is not a string it is simply returned.
(defun rst-adornment-level (key &optional add)
  (let ((fnd (assoc key rst-adornment-level-alist))
	(new 1))
    (cond
     ((not (stringp key))
      key)
     (fnd
      (cdr fnd))
     (add
      (while (rassoc new rst-adornment-level-alist)
	(setq new (1+ new)))
      (setq rst-adornment-level-alist
	    (append rst-adornment-level-alist (list (cons key new))))
      new))))

;; Classifies adornment for section titles and transitions. ADORNMENT is the
;; complete adornment string as found in the buffer. END is the point after the
;; last character of ADORNMENT. For overline section adornment LIMIT limits the
;; search for the matching underline. Returns a list. The first entry is t for
;; a transition, or a key string for `rst-adornment-level' for a section title.
;; The following eight values forming four match groups as can be used for
;; `set-match-data'. First match group contains the maximum points of the whole
;; construct. Second and last match group matched pure section title adornment
;; while third match group matched the section title text or the transition.
;; Each group but the first may or may not exist.
(defun rst-classify-adornment (adornment end limit)
  (save-excursion
    (save-match-data
      (goto-char end)
      (let ((ado-ch (aref adornment 0))
	    (ado-re (regexp-quote adornment))
	    (end-pnt (point))
	    (beg-pnt (progn
		       (forward-line 0)
		       (point)))
	    (nxt-emp
	     (save-excursion
	       (or (not (zerop (forward-line 1)))
		   (looking-at "\\s *$"))))
	    (prv-emp
	     (save-excursion
	       (or (not (zerop (forward-line -1)))
		   (looking-at "\\s *$"))))
	    key beg-ovr end-ovr beg-txt end-txt beg-und end-und)
	(cond
	 ((and nxt-emp prv-emp)
	  ;; A transition
	  (setq key t)
	  (setq beg-txt beg-pnt)
	  (setq end-txt end-pnt))
	 (prv-emp
	  ;; An overline
	  (setq key (concat (list ado-ch) "o"))
	  (setq beg-ovr beg-pnt)
	  (setq end-ovr end-pnt)
	  (forward-line 1)
	  (setq beg-txt (point))
	  (while (and (< (point) limit) (not end-txt))
	    (if (looking-at "\\s *$")
		;; No underline found
		(setq end-txt (1- (point)))
	      (when (looking-at (concat "\\(" ado-re "\\)\\s *$"))
		(setq end-und (match-end 1))
		(setq beg-und (point))
		(setq end-txt (1- beg-und))))
	    (forward-line 1)))
	 (t
	  ;; An underline
	  (setq key (concat (list ado-ch) "u"))
	  (setq beg-und beg-pnt)
	  (setq end-und end-pnt)
	  (setq end-txt (1- beg-und))
	  (setq beg-txt (progn
			  (if (re-search-backward "^\\s *$" 1 'move)
			      (forward-line 1))
			  (point)))))
	(list key
	      (or beg-ovr beg-txt beg-und)
	      (or end-und end-txt end-und)
	      beg-ovr end-ovr beg-txt end-txt beg-und end-und)))))

;; Handles adornments for font-locking section titles and transitions. Returns
;; three match groups. First and last match group matched pure overline /
;; underline adornment while second group matched section title text. Each
;; group may not exist.
(defun rst-font-lock-handle-adornment (limit)
  (let ((ado-pnt rst-font-lock-adornment-point))
    ;; May run only once - enforce this
    (setq rst-font-lock-adornment-point nil)
    (if ado-pnt
      (let* ((ado (rst-classify-adornment (match-string-no-properties 1)
					  ado-pnt limit))
	     (key (car ado))
	     (mtc (cdr ado)))
	(setq rst-font-lock-level (rst-adornment-level key t))
	(goto-char (nth 1 mtc))
	(set-match-data mtc)
	t))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;;; rst-mode.el ends here
