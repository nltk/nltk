;;; psvn.el --- Subversion interface for emacs
;; Copyright (C) 2002-2008 by Stefan Reichoer

;; Author: Stefan Reichoer <stefan@xsteve.at>
;; $Id: psvn.el 32032 2008-07-08 17:21:58Z xsteve $

;; psvn.el is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation; either version 2, or (at your option)
;; any later version.

;; psvn.el is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with GNU Emacs; see the file COPYING.  If not, write to
;; the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
;; Boston, MA 02111-1307, USA.

;;; Commentary

;; psvn.el is tested with GNU Emacs 21.3 on windows, debian linux,
;; freebsd5, red hat el4, ubuntu edgy with svn 1.4.0

;; psvn.el needs at least svn 1.1.0
;; if you upgrade to a higher version, you need to do a fresh checkout

;; psvn.el is an interface for the revision control tool subversion
;; (see http://subversion.tigris.org)
;; psvn.el provides a similar interface for subversion as pcl-cvs for cvs.
;; At the moment the following commands are implemented:
;;
;; M-x svn-status: run 'svn -status -v'
;; M-x svn-examine (like pcl-cvs cvs-examine) is alias for svn-status
;;
;; and show the result in the svn-status-buffer-name buffer (normally: *svn-status*).
;; If svn-status-verbose is set to nil, only "svn status" without "-v"
;; is run. Currently you have to toggle this variable manually.
;; This buffer uses svn-status mode in which the following keys are defined:
;; g     - svn-status-update:               run 'svn status -v'
;; M-s   - svn-status-update:               run 'svn status -v'
;; C-u g - svn-status-update:               run 'svn status -vu'
;; =     - svn-status-show-svn-diff         run 'svn diff'
;; l     - svn-status-show-svn-log          run 'svn log'
;; i     - svn-status-info                  run 'svn info'
;; r     - svn-status-revert                run 'svn revert'
;; X v   - svn-status-resolved              run 'svn resolved'
;; U     - svn-status-update-cmd            run 'svn update'
;; M-u   - svn-status-update-cmd            run 'svn update'
;; c     - svn-status-commit                run 'svn commit'
;; a     - svn-status-add-file              run 'svn add --non-recursive'
;; A     - svn-status-add-file-recursively  run 'svn add'
;; +     - svn-status-make-directory        run 'svn mkdir'
;; R     - svn-status-mv                    run 'svn mv'
;; C     - svn-status-cp                    run 'svn cp'
;; D     - svn-status-rm                    run 'svn rm'
;; M-c   - svn-status-cleanup               run 'svn cleanup'
;; k     - svn-status-lock                  run 'svn lock'
;; K     - svn-status-unlock                run 'svn unlock'
;; b     - svn-status-blame                 run 'svn blame'
;; X e   - svn-status-export                run 'svn export'
;; RET   - svn-status-find-file-or-examine-directory
;; ^     - svn-status-examine-parent
;; ~     - svn-status-get-specific-revision
;; E     - svn-status-ediff-with-revision
;; X X   - svn-status-resolve-conflicts
;; S g   - svn-status-grep-files
;; S s   - svn-status-search-files
;; s     - svn-status-show-process-buffer
;; h     - svn-status-pop-to-partner-buffer
;; e     - svn-status-toggle-edit-cmd-flag
;; ?     - svn-status-toggle-hide-unknown
;; _     - svn-status-toggle-hide-unmodified
;; m     - svn-status-set-user-mark
;; u     - svn-status-unset-user-mark
;; $     - svn-status-toggle-elide
;; w     - svn-status-copy-current-line-info
;; DEL   - svn-status-unset-user-mark-backwards
;; * !   - svn-status-unset-all-usermarks
;; * ?   - svn-status-mark-unknown
;; * A   - svn-status-mark-added
;; * M   - svn-status-mark-modified
;; * P   - svn-status-mark-modified-properties
;; * D   - svn-status-mark-deleted
;; * *   - svn-status-mark-changed
;; * .   - svn-status-mark-by-file-ext
;; * %   - svn-status-mark-filename-regexp
;; .     - svn-status-goto-root-or-return
;; f     - svn-status-find-file
;; o     - svn-status-find-file-other-window
;; C-o   - svn-status-find-file-other-window-noselect
;; v     - svn-status-view-file-other-window
;; I     - svn-status-parse-info
;; V     - svn-status-svnversion
;; P l   - svn-status-property-list
;; P s   - svn-status-property-set
;; P d   - svn-status-property-delete
;; P e   - svn-status-property-edit-one-entry
;; P i   - svn-status-property-ignore-file
;; P I   - svn-status-property-ignore-file-extension
;; P C-i - svn-status-property-edit-svn-ignore
;; P k   - svn-status-property-set-keyword-list
;; P K i - svn-status-property-set-keyword-id
;; P K d - svn-status-property-set-keyword-date
;; P y   - svn-status-property-set-eol-style
;; P x   - svn-status-property-set-executable
;; P m   - svn-status-property-set-mime-type
;; H     - svn-status-use-history
;; x     - svn-status-update-buffer
;; q     - svn-status-bury-buffer

;; C-x C-j - svn-status-dired-jump

;; The output in the buffer contains this header to ease reading
;; of svn output:
;;   FPH BASE CMTD Author   em File
;; F = Filemark
;; P = Property mark
;; H = History mark
;; BASE = local base revision
;; CMTD = last committed revision
;; Author = author of change
;; em = "**" or "(Update Available)" [see `svn-status-short-mod-flag-p']
;;      if file can be updated
;; File = path/filename
;;

;; To use psvn.el put the following line in your .emacs:
;; (require 'psvn)
;; Start the svn interface with M-x svn-status

;; The latest version of psvn.el can be found at:
;;   http://www.xsteve.at/prg/emacs/psvn.el
;; Or you can check it out from the subversion repository:
;;   svn co http://svn.collab.net/repos/svn/trunk/contrib/client-side/emacs emacs-svn

;; TODO:
;; * shortcut for svn propset svn:keywords "Date" psvn.el
;; * docstrings for the functions
;; * perhaps shortcuts for ranges, dates
;; * when editing the command line - offer help from the svn client
;; * finish svn-status-property-set
;; * Add repository browser
;; * Get rid of all byte-compiler warnings
;; * SVK working copy support
;; * multiple independent buffers in svn-status-mode
;; There are "TODO" comments in other parts of this file as well.

;; Overview over the implemented/not (yet) implemented svn sub-commands:
;; * add                       implemented
;; * blame                     implemented
;; * cat                       implemented
;; * checkout (co)             implemented
;; * cleanup                   implemented
;; * commit (ci)               implemented
;; * copy (cp)                 implemented
;; * delete (del, remove, rm)  implemented
;; * diff (di)                 implemented
;; * export                    implemented
;; * help (?, h)
;; * import                    used         (in svn-admin-create-trunk-directory)
;; * info                      implemented
;; * list (ls)                 implemented
;; * lock                      implemented
;; * log                       implemented
;; * merge
;; * mkdir                     implemented
;; * move (mv, rename, ren)    implemented
;; * propdel (pdel)            implemented
;; * propedit (pedit, pe)      not needed
;; * propget (pget, pg)        used         (in svn-status-property-edit)
;; * proplist (plist, pl)      implemented
;; * propset (pset, ps)        used         (in svn-prop-edit-do-it)
;; * resolved                  implemented
;; * revert                    implemented
;; * status (stat, st)         implemented
;; * switch (sw)
;; * unlock                    implemented
;; * update (up)               implemented

;; For the not yet implemented commands you should use the command line
;; svn client. If there are user requests for any missing commands I will
;; probably implement them.

;; There is also limited support for the web-based software project management and bug/issue tracking system trac
;; Trac ticket links can be enabled in the *svn-log* buffers when using the following:
;; (setq svn-log-link-handlers '(trac-ticket-short))

;; ---------------------------
;; Frequently asked questions:
;; ---------------------------

;; Q1: I need support for user names with blanks/spaces
;; A1: Add the user names to svn-user-names-including-blanks and set the
;;     svn-pre-parse-status-hook.
;;     The problem is, that the user names and the file names from the svn status
;;     output can both contain blanks. Blanks in file names are supported.
;;     the svn-user-names-including-blanks list is used to replace the spaces
;;     in the user names with - to overcome this problem

;; Q2: My svn-update command it taking a really long time. How can I
;;     see what's going on?
;; A2: In the *svn-status* buffer press "s".

;; Q3: How do I enter a username and password?
;; A3: In the *svn-status* buffer press "s", switch to the
;;     *svn-process* buffer and press enter. You will be prompted for
;;     username and password.

;; Q4: What does "?", "M", and "C" in the first column of the
;;     *svn-status* buffer mean?
;; A4: "?" means the file(s) is not under Subversion control
;;     "M" means you have a locally modified file
;;     "C" means there is a conflict
;;     "@$&#!" means someone is saying nasty things to you


;; Comments / suggestions and bug reports are welcome!

;; Development notes
;; -----------------

;; "svn-" is the package prefix used in psvn.el.  There are also longer
;; prefixes which clarify the code and help symbol completion, but they
;; are not intended to prevent name clashes with other packages.  All
;; interactive commands meant to be used only in a specific mode should
;; have names beginning with the name of that mode: for example,
;; "svn-status-add-file" in "svn-status-mode".  "psvn" should be used
;; only in names of files, customization groups, and features.  If SVK
;; support is ever added, it should use "svn-svk-" when no existing
;; prefix is applicable.

;; Many of the variables marked as `risky-local-variable' are probably
;; impossible to abuse, as the commands that read them are used only in
;; buffers that are not visiting any files.  Better safe than sorry.

;;; Code:

(require 'easymenu)

(eval-when-compile (require 'dired))
(eval-when-compile (require 'ediff-util))
(eval-when-compile (require 'ediff-wind))
(eval-when-compile (require 'elp))
(eval-when-compile (require 'pp))

(condition-case nil
    (progn
      (require 'diff-mode))
  (error nil))

(defconst svn-psvn-revision "$Id: psvn.el 32032 2008-07-08 17:21:58Z xsteve $"
  "The revision number of psvn.")

;;; user setable variables
(defcustom svn-status-verbose t
  "*Add '-v' to svn status call.
This can be toggled with \\[svn-status-toggle-svn-verbose-flag]."
  :type 'boolean
  :group 'psvn)
(defcustom svn-log-edit-file-name "++svn-log++"
  "*Name of a saved log file.
This can be either absolute, or relative to the default directory
of the `svn-log-edit-buffer-name' buffer."
  :type 'file
  :group 'psvn)
(put 'svn-log-edit-file-name 'risky-local-variable t)
(defcustom svn-log-edit-insert-files-to-commit t
  "*Insert the filelist to commit in the *svn-log* buffer"
  :type 'boolean
  :group 'psvn)
(defcustom svn-log-edit-show-diff-for-commit nil
  "*Show the diff being committed when you run `svn-status-commit.'."
  :type 'boolean
  :group 'psvn)
(defcustom svn-log-edit-use-log-edit-mode
  (and (condition-case nil (require 'log-edit) (error nil)) t)
  "*Use log-edit-mode as base for svn-log-edit-mode
This variable takes effect only when psvn.el is being loaded."
  :type 'boolean
  :group 'psvn)
(defcustom svn-log-edit-paragraph-start
  "$\\|[ \t]*$\\|##.*$\\|\\*.*:.*$\\|[ \t]+(.+):.*$"
  "*Value used for `paragraph-start' in `svn-log-edit-buffer-name' buffer."
  :type 'regexp
  :group 'psvn)
(defcustom svn-log-edit-paragraph-separate "$\\|##.*$"
  "*Value used for `paragraph-separate' in `svn-log-edit-buffer-name' buffer."
  :type 'regexp
  :group 'psvn)
(defcustom svn-status-hide-unknown nil
  "*Hide unknown files in `svn-status-buffer-name' buffer.
This can be toggled with \\[svn-status-toggle-hide-unknown]."
  :type 'boolean
  :group 'psvn)
(defcustom svn-status-hide-unmodified nil
  "*Hide unmodified files in `svn-status-buffer-name' buffer.
This can be toggled with \\[svn-status-toggle-hide-unmodified]."
  :type 'boolean
  :group 'psvn)
(defcustom svn-status-sort-status-buffer t
  "*Whether to sort the `svn-status-buffer-name' buffer.

Setting this variable to nil speeds up \\[M-x svn-status], however the
listing may then become incorrect.

This can be toggled with \\[svn-status-toggle-sort-status-buffer]."
  :type 'boolean
  :group 'psvn)

(defcustom svn-status-ediff-delete-temporary-files nil
  "*Whether to delete temporary ediff files. If set to ask, ask the user"
  :type '(choice (const t)
                 (const nil)
                 (const ask))
  :group 'psvn)

(defcustom svn-status-changelog-style 'changelog
  "*The changelog style that is used for `svn-file-add-to-changelog'.
Possible values are:
 'changelog: use `add-change-log-entry-other-window'
 'svn-dev: use commit messages that are used by the svn developers
 a function: This function is called to add a new entry to the changelog file.
"
  :type '(set (const changelog)
              (const svn-dev))
  :group 'psvn)

(defcustom svn-status-unmark-files-after-list '(commit revert)
  "*List of operations after which all user marks will be removed.
Possible values are: commit, revert."
  :type '(set (const commit)
              (const revert))
  :group 'psvn)

(defcustom svn-status-preserve-window-configuration t
  "*Try to preserve the window configuration."
  :type 'boolean
  :group 'psvn)

(defcustom svn-status-auto-revert-buffers t
  "*Auto revert buffers that have changed on disk."
  :type 'boolean
  :group 'psvn)

(defcustom svn-status-fancy-file-state-in-modeline t
  "*Show a color dot in the modeline that describes the state of the current file."
  :type 'boolean
  :group 'psvn)

(defcustom svn-status-negate-meaning-of-arg-commands '()
  "*List of operations that should use a negated meaning of the prefix argument.
The supported functions are `svn-status' and `svn-status-set-user-mark'."
  :type '(set (function-item svn-status)
              (function-item svn-status-set-user-mark))
  :group 'psvn)

(defcustom svn-status-svn-executable "svn"
  "*The name of the svn executable.
This can be either absolute or looked up on `exec-path'."
  ;; Don't use (file :must-match t).  It doesn't know about `exec-path'.
  :type 'file
  :group 'psvn)
(put 'svn-status-svn-executable 'risky-local-variable t)

(defcustom svn-status-default-export-directory "~/" "*The default directory that is suggested svn export."
  :type 'file
  :group 'psvn)

(defcustom svn-status-svn-environment-var-list '("LC_MESSAGES=C" "LC_ALL=")
  "*A list of environment variables that should be set for that svn process.
Each element is either a string \"VARIABLE=VALUE\" which will be added to
the environment when svn is run, or just \"VARIABLE\" which causes that
variable to be entirely removed from the environment.

The default setting is '(\"LC_MESSAGES=C\" \"LC_ALL=\"). This ensures that the svn command
line client does not output localized strings. psvn.el relies on the english
messages."
  :type '(repeat string)
  :group 'psvn)
(put 'svn-status-svn-environment-var-list 'risky-local-variable t)

(defcustom svn-browse-url-function nil
  ;; If the user hasn't changed `svn-browse-url-function', then changing
  ;; `browse-url-browser-function' should affect psvn even after it has
  ;; been loaded.
  "Function to display a Subversion related WWW page in a browser.
So far, this is used only for \"trac\" issue tracker integration.
By default, this is nil, which means use `browse-url-browser-function'.
Any non-nil value overrides that variable, with the same syntax."
  ;; It would be nice to show the full list of browsers supported by
  ;; browse-url, but (custom-variable-type 'browse-url-browser-function)
  ;; returns just `function' if browse-url has not yet been loaded,
  ;; and there seems to be no easy way to autoload browse-url when
  ;; the custom-type of svn-browse-url-function is actually needed.
  ;; So I'll only offer enough choices to cover all supported types.
  :type `(choice (const :tag "Specified by `browse-url-browser-function'" nil)
                 (function :value browse-url-default-browser
                           ;; In XEmacs 21.4.17, the `function' widget matches
                           ;; all objects.  Constrain it here so that alists
                           ;; fall through to the next choice.  Accept either
                           ;; a symbol (fbound or not) or a lambda expression.
                           :match ,(lambda (widget value)
                                     (or (symbolp value) (functionp value))))
                 (svn-alist :tag "Regexp/function association list"
                            :key-type regexp :value-type function
                            :value (("." . browse-url-default-browser))))
  :link '(emacs-commentary-link "browse-url")
  :group 'psvn)
;; (put 'svn-browse-url-function 'risky-local-variable t)
;; already implied by "-function" suffix

(defcustom svn-status-window-alist
  '((diff "*svn-diff*") (log "*svn-log*") (info t) (blame t) (proplist t) (update t))
  "An alist to specify which windows should be used for svn command outputs.
The following keys are supported: diff, log, info, blame, proplist, update.
The following values can be given:
nil       ... show in `svn-process-buffer-name' buffer
t         ... show in dedicated *svn-info* buffer
invisible ... don't show the buffer (eventually useful for update)
a string  ... show in a buffer named string"
  :type '(svn-alist
          :key-type symbol
          :value-type (group
                       (choice
                        (const :tag "Show in *svn-process* buffer" nil)
                        (const :tag "Show in dedicated *svn-info* buffer" t)
                        (const :tag "Don't show the output" invisible)
                        (string :tag "Show in a buffer named"))))
  :options '(diff log info blame proplist update)
  :group 'psvn)

(defcustom svn-status-short-mod-flag-p t
  "*Whether the mark for out of date files is short or long.

If this variable is is t, and a file is out of date (i.e., there is a newer
version in the repository than the working copy), then the file will
be marked by \"**\"

If this variable is nil, and the file is out of date then the longer phrase
\"(Update Available)\" is used.

In either case the mark gets the face
`svn-status-update-available-face', and will only be visible if
`\\[svn-status-update]' is run with a prefix argument"
  :type '(choice (const :tag "Short \"**\"" t)
                 (const :tag "Long \"(Update Available)\"" nil))
  :group 'psvn)

(defvar svn-status-debug-level 0 "The psvn.el debugging verbosity level.
The higher the number, the more debug messages are shown.

See `svn-status-message' for the meaning of values for that variable.")

(defvar svn-bookmark-list nil "A list of locations for a quick access via `svn-status-via-bookmark'")
;;(setq svn-bookmark-list '(("proj1" . "~/work/proj1")
;;                          ("doc1" . "~/docs/doc1")))

(defvar svn-status-buffer-name "*svn-status*" "Name for the svn status buffer")
(defvar svn-process-buffer-name " *svn-process*" "Name for the svn process buffer")
(defvar svn-log-edit-buffer-name "*svn-log-edit*" "Name for the svn log-edit buffer")

(defcustom svn-status-use-header-line
  (if (boundp 'header-line-format) t 'inline)
  "*Whether a header line should be used.
When t: Use the emacs header line
When 'inline: Insert the header line in the `svn-status-buffer-name' buffer
Otherwise: Don't display a header line"
  :type '(choice (const :tag "Show column titles as a header line" t)
                 (const :tag "Insert column titles as text in the buffer" inline)
                 (other :tag "No column titles" nil))
  :group 'psvn)

;;; default arguments to pass to svn commands
;; TODO: When customizing, an option menu or completion might be nice....
(defcustom svn-status-default-log-arguments '("-v")
  "*List of arguments to pass to svn log.
\(used in `svn-status-show-svn-log'; override these by giving prefixes\)."
  :type '(repeat string)
  :group 'psvn)
(put 'svn-status-default-log-arguments 'risky-local-variable t)

(defcustom svn-status-default-commit-arguments '()
  "*List of arguments to pass to svn commit.
If you don't like recursive commits, set this value to (\"-N\")
or mark the directory before committing it.
Do not put an empty string here, except as an argument of an option:
Subversion and the operating system may treat that as a file name
equivalent to \".\", so you would commit more than you intended."
  :type '(repeat string)
  :group 'psvn)
(put 'svn-status-default-commit-arguments 'risky-local-variable t)

(defcustom svn-status-default-diff-arguments '("-x" "--ignore-eol-style")
  "*A list of arguments that is passed to the svn diff command.
When the built in diff command is used,
the following options are available: --ignore-eol-style, --ignore-space-change,
--ignore-all-space, --ignore-eol-style.
The following setting ignores eol style changes and all white space changes:
'(\"-x\" \"--ignore-eol-style --ignore-all-space\")

If you'd like to suppress whitespace changes using the external diff command
use the following value:
'(\"--diff-cmd\" \"diff\" \"-x\" \"-wbBu\")

"
  :type '(repeat string)
  :group 'psvn)
(put 'svn-status-default-diff-arguments 'risky-local-variable t)

(defcustom svn-status-default-status-arguments '()
  "*A list of arguments that is passed to the svn status command.
The following options are available: --ignore-externals

"
  :type '(repeat string)
  :group 'psvn)
(put 'svn-status-default-status-arguments 'risky-local-variable t)

(defcustom svn-status-default-blame-arguments '("-x" "--ignore-eol-style")
  "*A list of arguments that is passed to the svn blame command.
See `svn-status-default-diff-arguments' for some examples."
  :type '(repeat string)
  :group 'psvn)

(put 'svn-status-default-blame-arguments 'risky-local-variable t)

(defvar svn-trac-project-root nil
  "Path for an eventual existing trac issue tracker.
This can be set with \\[svn-status-set-trac-project-root].")

(defvar svn-status-module-name nil
  "*A short name for the actual project.
This can be set with \\[svn-status-set-module-name].")

(defvar svn-status-branch-list nil
  "*A list of known branches for the actual project
This can be set with \\[svn-status-set-branch-list].

The list contains full repository paths or shortcuts starting with \#
\# at the beginning is replaced by the repository url.
\#1\# has the special meaning that all paths below the given directory
will be considered for interactive selections.

A useful setting might be: '\(\"\#trunk\" \"\#1\#tags\" \"\#1\#branches\")")

(defvar svn-status-load-state-before-svn-status t
  "*Whether to automatically restore state from ++psvn.state file before running svn-status.")

(defvar svn-log-link-handlers nil "A list of link handlers in *svn-log* buffers.
These link handlers must be registered via `svn-log-register-link-handler'")

;;; hooks
(defvar svn-status-mode-hook nil "Hook run when entering `svn-status-mode'.")
(defvar svn-log-edit-mode-hook nil "Hook run when entering `svn-log-edit-mode'.")
(defvar svn-log-edit-done-hook nil "Hook run after commiting files via svn.")
;; (put 'svn-log-edit-mode-hook 'risky-local-variable t)
;; (put 'svn-log-edit-done-hook 'risky-local-variable t)
;; already implied by "-hook" suffix

(defvar svn-post-process-svn-output-hook nil "Hook that can be used to preprocess the output from svn.
The function `svn-status-remove-control-M' can be useful for that hook")

(when (eq system-type 'windows-nt)
  (add-hook 'svn-post-process-svn-output-hook 'svn-status-remove-control-M))

(defvar svn-status-svn-process-coding-system (when (boundp 'locale-coding-system) locale-coding-system)
  "The coding system that is used for the svn command line client.
It is used in svn-run, if it is not nil.")

(defvar svn-status-svn-file-coding-system 'undecided-unix
  "The coding system that is used to save files that are loaded as
parameter or data files via the svn command line client.
It is used in the following functions: `svn-prop-edit-do-it', `svn-log-edit-done'.
You could set it to 'utf-8")

(defcustom svn-status-use-ido-completion
  (fboundp 'ido-completing-read)
  "*Use ido completion functionality."
  :type 'boolean
  :group 'psvn)

(defvar svn-status-completing-read-function
  (if svn-status-use-ido-completion 'ido-completing-read 'completing-read))

;;; experimental features
(defvar svn-status-track-user-input nil "Track user/password queries.
This feature is implemented via a process filter.
It is an experimental feature.")

(defvar svn-status-refresh-info nil "Whether `svn-status-update-buffer' should call `svn-status-parse-info'.")

;;; Customize group
(defgroup psvn nil
  "Subversion interface for Emacs."
  :group 'tools)

(defgroup psvn-faces nil
  "psvn faces."
  :group 'psvn)


(eval-and-compile
  (require 'cl)
  (defconst svn-xemacsp (featurep 'xemacs))
  (if svn-xemacsp
      (require 'overlay)
    (require 'overlay nil t)))

(defcustom svn-status-display-full-path nil
  "Specifies how the filenames look like in the listing.
If t, their full path name will be displayed, else only the filename."
  :type 'boolean
  :group 'psvn)

(defcustom svn-status-prefix-key [(control x) (meta s)]
  "Prefix key for the psvn commands in the global keymap."
  :type '(choice (const [(control x) ?v ?S])
                 (const [(super s)])
                 (const [(hyper s)])
                 (const [(control x) ?v])
                 (const [(control x) ?V])
                 (sexp))
  :group 'psvn
  :set  (lambda (var value)
          (if (boundp var)
              (global-unset-key (symbol-value var)))
          (set var value)
          (global-set-key (symbol-value var) 'svn-global-keymap)))

(defcustom svn-admin-default-create-directory "~/"
  "*The default directory that is suggested for `svn-admin-create'."
  :type 'string
  :group 'psvn)

(defvar svn-status-custom-hide-function nil
  "A function that receives a line-info and decides whether to hide that line.
See psvn.el for an example function.")
;; (put 'svn-status-custom-hide-function 'risky-local-variable t)
;; already implied by "-function" suffix


;; Use the normally used mode for files ending in .~HEAD~, .~BASE~, ...
(add-to-list 'auto-mode-alist '("\\.~?\\(HEAD\\|BASE\\|PREV\\)~?\\'" ignore t))

;;; internal variables
(defvar svn-status-directory-history nil "List of visited svn working directories.")
(defvar svn-process-cmd nil)
(defvar svn-status-info nil)
(defvar svn-status-filename-to-buffer-position-cache (make-hash-table :test 'equal :weakness t))
(defvar svn-status-base-info nil "The parsed result from the svn info command.")
(defvar svn-status-initial-window-configuration nil)
(defvar svn-status-default-column 23)
(defvar svn-status-default-revision-width 4)
(defvar svn-status-default-author-width 9)
(defvar svn-status-line-format " %c%c%c %4s %4s %-9s")
(defvar svn-start-of-file-list-line-number 0)
(defvar svn-status-files-to-commit nil
  "List of files to commit at `svn-log-edit-done'.
This is always set together with `svn-status-recursive-commit'.")
(defvar svn-status-recursive-commit nil
  "Non-nil if the next commit should be recursive.
This is always set together with `svn-status-files-to-commit'.")
(defvar svn-log-edit-update-log-entry nil
  "Revision number whose log entry is being edited.
This is nil if the log entry is for a new commit.")
(defvar svn-status-pre-commit-window-configuration nil)
(defvar svn-status-pre-propedit-window-configuration nil)
(defvar svn-status-head-revision nil)
(defvar svn-status-root-return-info nil)
(defvar svn-status-property-edit-must-match-flag nil)
(defvar svn-status-propedit-property-name nil "The property name for the actual svn propset command")
(defvar svn-status-propedit-file-list nil)
(defvar svn-status-mode-line-process "")
(defvar svn-status-mode-line-process-status "")
(defvar svn-status-mode-line-process-edit-flag "")
(defvar svn-status-edit-svn-command nil)
(defvar svn-status-update-previous-process-output nil)
(defvar svn-pre-run-asynch-recent-keys nil)
(defvar svn-pre-run-mode-line-process nil)
(defvar svn-status-temp-dir
  (expand-file-name
   (or
    (when (boundp 'temporary-file-directory) temporary-file-directory) ;emacs
    ;; XEmacs 21.4.17 can return "/tmp/kalle" from (temp-directory).
    ;; `file-name-as-directory' adds a slash so we can append a file name.
    (when (fboundp 'temp-directory) (file-name-as-directory (temp-directory)))
    "/tmp/")) "The directory that is used to store temporary files for psvn.")
;; Because `temporary-file-directory' is not a risky local variable in
;; GNU Emacs 22.0.51, we don't mark `svn-status-temp-dir' as such either.
(defvar svn-temp-suffix (make-temp-name "."))
(put 'svn-temp-suffix 'risky-local-variable t)
(defvar svn-status-temp-file-to-remove nil)
(put 'svn-status-temp-file-to-remove 'risky-local-variable t)
(defvar svn-status-temp-arg-file (concat svn-status-temp-dir "svn.arg" svn-temp-suffix))
(put 'svn-status-temp-arg-file 'risky-local-variable t)
(defvar svn-status-options nil)
(defvar svn-status-remote)
(defvar svn-status-commit-rev-number nil)
(defvar svn-status-update-rev-number nil)
(defvar svn-status-operated-on-dot nil)
(defvar svn-status-last-commit-author nil)
(defvar svn-status-elided-list nil)
(defvar svn-status-last-output-buffer-name nil "The buffer name for the buffer that holds the output from the last executed svn command")
(defvar svn-status-pre-run-svn-buffer nil)
(defvar svn-status-update-list nil)
(defvar svn-transient-buffers)
(defvar svn-ediff-windows)
(defvar svn-ediff-result)
(defvar svn-status-last-diff-options nil)
(defvar svn-status-blame-file-name nil)
(defvar svn-admin-last-repository-dir nil "The last repository url for various operations.")
(defvar svn-last-cmd-ring (make-ring 30) "Ring that holds the last executed svn commands (for debugging purposes)")
(defvar svn-status-cached-version-string nil)
(defvar svn-client-version nil "The version number of the used svn client")
(defvar svn-status-get-line-information-for-file nil)
(defvar svn-status-base-dir-cache (make-hash-table :test 'equal :weakness nil))
(defvar svn-log-registered-link-handlers (make-hash-table :test 'eql :weakness nil))

(defvar svn-status-partner-buffer nil "The partner buffer for this svn related buffer")
(make-variable-buffer-local 'svn-status-partner-buffer)

;; Emacs 21 defines these in ediff-init.el but it seems more robust
;; to just declare the variables here than try to load that file.
;; It is Ediff's job to declare these as risky-local-variable if needed.
(defvar ediff-buffer-A)
(defvar ediff-buffer-B)
(defvar ediff-buffer-C)
(defvar ediff-quit-hook)

;; Ditto for log-edit.el.
(defvar log-edit-initial-files)
(defvar log-edit-callback)
(defvar log-edit-listfun)

;; Ediff does not use this variable in GNU Emacs 20.7, GNU Emacs 21.4,
;; nor XEmacs 21.4.17.  However, pcl-cvs (a.k.a. pcvs) does.
;; TODO: Check if this should be moved into the "svn-" namespace.
(defvar ediff-after-quit-destination-buffer)

;; That is an example for the svn-status-custom-hide-function:
;; Note: For many cases it is a better solution to ignore files or
;; file extensions via the svn-ignore properties (on P i, P I)
;; (setq svn-status-custom-hide-function 'svn-status-hide-pyc-files)
;; (defun svn-status-hide-pyc-files (info)
;;   "Hide all pyc files in the `svn-status-buffer-name' buffer."
;;   (let* ((fname (svn-status-line-info->filename-nondirectory info))
;;          (fname-len (length fname)))
;;     (and (> fname-len 4) (string= (substring fname (- fname-len 4)) ".pyc"))))

;;; faces
(defface svn-status-marked-face
  '((((type tty) (class color)) (:foreground "green" :weight light))
    (((class color) (background light)) (:foreground "green3"))
    (((class color) (background dark)) (:foreground "palegreen2"))
    (t (:weight bold)))
  "Face to highlight the mark for user marked files in svn status buffers."
  :group 'psvn-faces)

(defface svn-status-marked-popup-face
  '((((type tty) (class color)) (:foreground "green" :weight light))
    (((class color) (background light)) (:foreground "green3"))
    (((class color) (background dark)) (:foreground "palegreen2"))
    (t (:weight bold)))
  "Face to highlight the actual file, if a popup menu is activated."
  :group 'psvn-faces)

(defface svn-status-update-available-face
  '((((type tty) (class color)) (:foreground "magenta" :weight light))
    (((class color) (background light)) (:foreground "magenta"))
    (((class color) (background dark)) (:foreground "yellow"))
    (t (:weight bold)))
  "Face used to highlight the 'out of date' mark.
\(i.e., the mark used when there is a newer version in the repository
than the working copy.\)

See also `svn-status-short-mod-flag-p'."
  :group 'psvn-faces)

;based on cvs-filename-face
(defface svn-status-directory-face
  '((((type tty) (class color)) (:foreground "lightblue" :weight light))
    (((class color) (background light)) (:foreground "blue4"))
    (((class color) (background dark)) (:foreground "lightskyblue1"))
    (t (:weight bold)))
  "Face for directories in *svn-status* buffers.
See `svn-status--line-info->directory-p' for what counts as a directory."
  :group 'psvn-faces)

;based on font-lock-comment-face
(defface svn-status-filename-face
  '((((class color) (background light)) (:foreground "chocolate"))
    (((class color) (background dark)) (:foreground "beige")))
  "Face for non-directories in *svn-status* buffers.
See `svn-status--line-info->directory-p' for what counts as a directory."
  :group 'psvn-faces)

;not based on anything, may be horribly ugly!
(defface svn-status-symlink-face
  '((((class color) (background light)) (:foreground "cornflower blue"))
    (((class color) (background dark)) (:foreground "cyan")))
  "Face for symlinks in *svn-status* buffers.

This is the face given to the actual link (i.e., the versioned item),
the target of the link gets either `svn-status-filename-face' or
`svn-status-directory-face'."
  :group 'psvn-faces)

;based on font-lock-warning-face
(defface svn-status-locked-face
  '((t
     (:weight bold :foreground "Red")))
  "Face for the phrase \"[ LOCKED ]\" `svn-status-buffer-name' buffers."
  :group 'psvn-faces)

;based on vhdl-font-lock-directive-face
(defface svn-status-switched-face
  '((((class color)
      (background light))
     (:foreground "CadetBlue"))
    (((class color)
      (background dark))
     (:foreground "Aquamarine"))
    (t
     (:bold t :italic t)))
  "Face for the phrase \"(switched)\" non-directories in svn status buffers."
  :group 'psvn-faces)

(if svn-xemacsp
    (defface svn-status-blame-highlight-face
      '((((type tty) (class color)) (:foreground "green" :weight light))
        (((class color) (background light)) (:foreground "green3"))
        (((class color) (background dark)) (:foreground "palegreen2"))
        (t (:weight bold)))
      "Default face for highlighting a line in svn status blame mode."
      :group 'psvn-faces)
  (defface svn-status-blame-highlight-face
    '((t :inherit highlight))
    "Default face for highlighting a line in svn status blame mode."
    :group 'psvn-faces))

(defface svn-status-blame-rev-number-face
  '((((class color) (background light)) (:foreground "DarkGoldenrod"))
    (((class color) (background dark)) (:foreground "LightGoldenrod"))
    (t (:weight bold :slant italic)))
  "Face to highlight revision numbers in the svn-blame mode."
  :group 'psvn-faces)

(defvar svn-highlight t)
;; stolen from PCL-CVS
(defun svn-add-face (str face &optional keymap)
  "Return string STR decorated with the specified FACE.
If `svn-highlight' is nil then just return STR."
  (when svn-highlight
    ;; Do not use `list*'; cl.el might not have been loaded.  We could
    ;; put (require 'cl) at the top but let's try to manage without.
    (add-text-properties 0 (length str)
                         `(face ,face
                                mouse-face highlight)
;; 18.10.2004: the keymap parameter is not used (yet) in psvn.el
;;                           ,@(when keymap
;;                               `(mouse-face highlight
;;                                 local-map ,keymap)))
                         str))
  str)

(defun svn-status-maybe-add-face (condition text face)
  "If CONDITION then add FACE to TEXT.
Else return TEXT unchanged."
  (if condition
      (svn-add-face text face)
    text))

(defun svn-status-choose-face-to-add (condition text face1 face2)
  "If CONDITION then add FACE1 to TEXT, else add FACE2 to TEXT."
  (if condition
      (svn-add-face text face1)
    (svn-add-face text face2)))

(defun svn-status-maybe-add-string (condition string face)
  "If CONDITION then return STRING decorated with FACE.
Otherwise, return \"\"."
  (if condition
      (svn-add-face string face)
    ""))

;; compatibility
;; emacs 20
(defalias 'svn-point-at-eol
  (if (fboundp 'point-at-eol) 'point-at-eol 'line-end-position))
(defalias 'svn-point-at-bol
  (if (fboundp 'point-at-bol) 'point-at-bol 'line-beginning-position))
(defalias 'svn-read-directory-name
  (if (fboundp 'read-directory-name) 'read-directory-name 'read-file-name))

(eval-when-compile
  (if (not (fboundp 'gethash))
      (require 'cl-macs)))
(defalias 'svn-puthash (if (fboundp 'puthash) 'puthash 'cl-puthash))

;; emacs 21
(if (fboundp 'line-number-at-pos)
    (defalias 'svn-line-number-at-pos 'line-number-at-pos)
  (defun svn-line-number-at-pos (&optional pos)
    "Return (narrowed) buffer line number at position POS.
If POS is nil, use current buffer location."
    (let ((opoint (or pos (point))) start)
      (save-excursion
        (goto-char (point-min))
        (setq start (point))
        (goto-char opoint)
        (forward-line 0)
        (1+ (count-lines start (point)))))))

(defun svn-substring-no-properties (string &optional from to)
  (if (fboundp 'substring-no-properties)
      (substring-no-properties string from to)
    (substring string from to)))

; xemacs
;; Evaluate the defsubst at compile time, so that the byte compiler
;; knows the definition and can inline calls.  It cannot detect the
;; defsubst automatically from within the if form.
(eval-and-compile
  (if (fboundp 'match-string-no-properties)
      (defalias 'svn-match-string-no-properties 'match-string-no-properties)
    (defsubst svn-match-string-no-properties (match)
      (buffer-substring-no-properties (match-beginning match) (match-end match)))))

;; XEmacs 21.4.17 does not have an `alist' widget.  Define a replacement.
;; To find out whether the `alist' widget exists, we cannot check just
;; (get 'alist 'widget-type), because GNU Emacs 21.4 defines it in
;; "wid-edit.el", which is not preloaded; it will be autoloaded when
;; `widget-create' is called.  Instead, we call `widgetp', which is
;; also autoloaded from "wid-edit.el".  XEmacs 21.4.17 does not have
;; `widgetp' either, so we check that first.
(if (and (fboundp 'widgetp) (widgetp 'alist))
    (define-widget 'svn-alist 'alist
      "An association list.
Use this instead of `alist', for XEmacs 21.4 compatibility.")
  (define-widget 'svn-alist 'list
    "An association list.
Use this instead of `alist', for XEmacs 21.4 compatibility."
    :convert-widget 'svn-alist-convert-widget
    :tag "Association List"
    :key-type 'sexp
    :value-type 'sexp)
  (defun svn-alist-convert-widget (widget)
    (let* ((value-type (widget-get widget :value-type))
           (option-widgets (loop for option in (widget-get widget :options)
                             collect `(cons :format "%v"
                                            (const :format "%t: %v\n"
                                                   :tag "Key"
                                                   ,option)
                                            ,value-type))))
      (widget-put widget :args
                  `(,@(when option-widgets
                        `((set :inline t :format "%v"
                               ,@option-widgets)))
                    (editable-list :inline t
                                   (cons :format "%v"
                                         ,(widget-get widget :key-type)
                                         ,value-type)))))
    widget))

;; process launch functions
(defvar svn-call-process-function (if (fboundp 'process-file) 'process-file 'call-process))
(defvar svn-start-process-function (if (fboundp 'start-file-process) 'start-file-process 'start-process))


;;; keymaps

(defvar svn-global-keymap nil "Global keymap for psvn.el.
To bind this to a different key, customize `svn-status-prefix-key'.")
(put 'svn-global-keymap 'risky-local-variable t)
(when (not svn-global-keymap)
  (setq svn-global-keymap (make-sparse-keymap))
  (define-key svn-global-keymap (kbd "v") 'svn-status-version)
  (define-key svn-global-keymap (kbd "s") 'svn-status-this-directory)
  (define-key svn-global-keymap (kbd "b") 'svn-status-via-bookmark)
  (define-key svn-global-keymap (kbd "h") 'svn-status-use-history)
  (define-key svn-global-keymap (kbd "u") 'svn-status-update-cmd)
  (define-key svn-global-keymap (kbd "=") 'svn-status-show-svn-diff)
  (define-key svn-global-keymap (kbd "f =") 'svn-file-show-svn-diff)
  (define-key svn-global-keymap (kbd "f e") 'svn-file-show-svn-ediff)
  (define-key svn-global-keymap (kbd "f l") 'svn-status-show-svn-log)
  (define-key svn-global-keymap (kbd "f b") 'svn-status-blame)
  (define-key svn-global-keymap (kbd "f a") 'svn-file-add-to-changelog)
  (define-key svn-global-keymap (kbd "c") 'svn-status-commit)
  (define-key svn-global-keymap (kbd "S") 'svn-status-switch-to-status-buffer)
  (define-key svn-global-keymap (kbd "o") 'svn-status-pop-to-status-buffer))

(defvar svn-status-diff-mode-map ()
  "Keymap used in `svn-status-diff-mode' for additional commands that are not defined in diff-mode.")
(put 'svn-status-diff-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-status-diff-mode-map)
  (setq svn-status-diff-mode-map (copy-keymap diff-mode-shared-map))
  (define-key svn-status-diff-mode-map [?g] 'revert-buffer)
  (define-key svn-status-diff-mode-map [?s] 'svn-status-pop-to-status-buffer)
  (define-key svn-status-diff-mode-map [?c] 'svn-status-diff-pop-to-commit-buffer)
  (define-key svn-status-diff-mode-map [?w] 'svn-status-diff-save-current-defun-as-kill))

(defvar svn-global-trac-map ()
  "Subkeymap used in `svn-global-keymap' for trac issue tracker commands.")
(put 'svn-global-trac-map 'risky-local-variable t) ;for Emacs 20.7
(when (not svn-global-trac-map)
  (setq svn-global-trac-map (make-sparse-keymap))
  (define-key svn-global-trac-map (kbd "w") 'svn-trac-browse-wiki)
  (define-key svn-global-trac-map (kbd "t") 'svn-trac-browse-timeline)
  (define-key svn-global-trac-map (kbd "m") 'svn-trac-browse-roadmap)
  (define-key svn-global-trac-map (kbd "s") 'svn-trac-browse-source)
  (define-key svn-global-trac-map (kbd "r") 'svn-trac-browse-report)
  (define-key svn-global-trac-map (kbd "i") 'svn-trac-browse-ticket)
  (define-key svn-global-trac-map (kbd "c") 'svn-trac-browse-changeset)
  (define-key svn-global-keymap (kbd "t") svn-global-trac-map))

;; The setter of `svn-status-prefix-key' makes a binding in the global
;; map refer to the `svn-global-keymap' symbol, rather than directly
;; to the keymap.  Emacs then implicitly uses the symbol-function.
;; This has the advantage that `describe-bindings' (C-h b) can show
;; the name of the keymap and link to its documentation.
(defalias 'svn-global-keymap svn-global-keymap)
;; `defalias' of GNU Emacs 21.4 doesn't allow a docstring argument.
(put 'svn-global-keymap 'function-documentation
     '(documentation-property 'svn-global-keymap 'variable-documentation t))


;; named after SVN_WC_ADM_DIR_NAME in svn_wc.h
(defun svn-wc-adm-dir-name ()
  "Return the name of the \".svn\" subdirectory or equivalent."
  (if (and (eq system-type 'windows-nt)
           (getenv "SVN_ASP_DOT_NET_HACK"))
      "_svn"
    ".svn"))

(defun svn-log-edit-file-name (&optional curdir)
  "Get the name of the saved log edit file
If curdir, return `svn-log-edit-file-name'
Otherwise position svn-log-edit-file-name in the root directory of this working copy"
  (if curdir
      svn-log-edit-file-name
    (concat (svn-status-base-dir) svn-log-edit-file-name)))

(defun svn-status-message (level &rest args)
  "If LEVEL is lower than `svn-status-debug-level' print ARGS using `message'.

Guideline for numbers:
1 - error messages, 3 - non-serious error messages, 5 - messages for things
that take a long time, 7 - not very important messages on stuff, 9 - messages
inside loops."
  (if (<= level svn-status-debug-level)
      (apply 'message args)))

(defun svn-status-flatten-list (list)
  "Flatten any lists within ARGS, so that there are no sublists."
  (loop for item in list
        if (listp item) nconc (svn-status-flatten-list item)
        else collect item))

(defun svn-status-window-line-position (w)
  "Return the window line at point for window W, or nil if W is nil."
  (svn-status-message 3 "About to count lines; selected window is %s" (selected-window))
  (and w (count-lines (window-start w) (point))))

;;;###autoload
(defun svn-checkout (repos-url path)
  "Run svn checkout REPOS-URL PATH."
  (interactive (list (read-string "Checkout from repository Url: ")
                     (svn-read-directory-name "Checkout to directory: ")))
  (svn-run t t 'checkout "checkout" repos-url (expand-file-name path)))

;;;###autoload (defalias 'svn-examine 'svn-status)
(defalias 'svn-examine 'svn-status)

;;;###autoload
(defun svn-status (dir &optional arg)
  "Examine the status of Subversion working copy in directory DIR.
If ARG is -, allow editing of the parameters. One could add -N to
run svn status non recursively to make it faster.
For every other non nil ARG pass the -u argument to `svn status', which
asks svn to connect to the repository and check to see if there are updates
there.

If there is no .svn directory, examine if there is CVS and run
`cvs-examine'. Otherwise ask if to run `dired'."
  (interactive (list (svn-read-directory-name "SVN status directory: "
                                              nil default-directory nil)
                     current-prefix-arg))
  (let ((svn-dir (format "%s%s"
                         (file-name-as-directory dir)
                         (svn-wc-adm-dir-name)))
        (cvs-dir (format "%sCVS" (file-name-as-directory dir))))
    (cond
     ((file-directory-p svn-dir)
      (setq arg (svn-status-possibly-negate-meaning-of-arg arg 'svn-status))
      (svn-status-1 dir arg))
     ((and (file-directory-p cvs-dir)
           (fboundp 'cvs-examine))
      (cvs-examine dir nil))
     (t
      (when (y-or-n-p
             (format
              (concat
               "%s "
               "is not Subversion controlled (missing %s "
               "directory). "
               "Run dired instead? ")
              dir
              (svn-wc-adm-dir-name)))
        (dired dir))))))

(defvar svn-status-display-new-status-buffer nil)
(defun svn-status-1 (dir &optional arg)
  "Examine DIR. See `svn-status' for more information."
  (unless (file-directory-p dir)
    (error "%s is not a directory" dir))
  (setq dir (file-name-as-directory dir))
  (when svn-status-load-state-before-svn-status
    (unless (string= dir (car svn-status-directory-history))
      (let ((default-directory dir))    ;otherwise svn-status-base-dir looks in the wrong place
        (svn-status-load-state t))))
  (setq svn-status-directory-history (delete dir svn-status-directory-history))
  (add-to-list 'svn-status-directory-history dir)
  (if (string= (buffer-name) svn-status-buffer-name)
      (setq svn-status-display-new-status-buffer nil)
    (setq svn-status-display-new-status-buffer t)
    ;;(message "psvn: Saving initial window configuration")
    (setq svn-status-initial-window-configuration
          (current-window-configuration)))
  (let* ((cur-buf (current-buffer))
         (status-buf (get-buffer-create svn-status-buffer-name))
         (proc-buf (get-buffer-create svn-process-buffer-name))
         (want-edit (eq arg '-))
         (status-option (if want-edit
                            (if svn-status-verbose "-v" "")
                          (if svn-status-verbose
                              (if arg "-uv" "-v")
                            (if arg "-u" "")))))
    (save-excursion
      (set-buffer status-buf)
      (setq default-directory dir)
      (set-buffer proc-buf)
      (setq default-directory dir
            svn-status-remote (when arg t))
      (set-buffer cur-buf)
      (if want-edit
          (let (svn-status-edit-svn-command t)
            (svn-run t t 'status "status" svn-status-default-status-arguments status-option))
        (svn-run t t 'status "status" svn-status-default-status-arguments status-option)))))

(defun svn-status-this-directory (arg)
  "Run `svn-status' for the `default-directory'"
  (interactive "P")
  (svn-status default-directory arg))

(defun svn-status-use-history ()
  "Interactively select a different directory from `svn-status-directory-history'."
  (interactive)
  (let* ((in-status-buffer (eq major-mode 'svn-status-mode))
         (hist (if in-status-buffer (cdr svn-status-directory-history) svn-status-directory-history))
         (dir (funcall svn-status-completing-read-function "svn-status on directory: " hist))
         (svn-status-buffer (get-buffer svn-status-buffer-name))
         (svn-buffer-available (and svn-status-buffer
                                    (with-current-buffer svn-status-buffer-name (string= default-directory dir)))))
    (if (file-directory-p dir)
        (if svn-buffer-available
            (svn-status-switch-to-status-buffer)
          (unless svn-status-refresh-info
            (setq svn-status-refresh-info 'once))
          (svn-status dir))
      (error "%s is not a directory" dir))))

(defun svn-had-user-input-since-asynch-run ()
  (not (equal (recent-keys) svn-pre-run-asynch-recent-keys)))

(defun svn-process-environment ()
  "Construct the environment for the svn process.
It is a combination of `svn-status-svn-environment-var-list' and
the usual `process-environment'."
  ;; If there are duplicate elements in `process-environment', then GNU
  ;; Emacs 21.4 guarantees that the first one wins; but GNU Emacs 20.7
  ;; and XEmacs 21.4.17 don't document what happens.  We'll just remove
  ;; any duplicates ourselves, then.  This also gives us an opportunity
  ;; to handle the "VARIABLE" syntax that none of them supports.
  (loop with found = '()
        for elt in (append svn-status-svn-environment-var-list
                           process-environment)
        for has-value = (string-match "=" elt)
        for name = (substring elt 0 has-value)
        unless (member name found)
          do (push name found)
          and when has-value
            collect elt))

(defun svn-run (run-asynchron clear-process-buffer cmdtype &rest arglist)
  "Run svn with arguments ARGLIST.

If RUN-ASYNCHRON is t then run svn asynchronously.

If CLEAR-PROCESS-BUFFER is t then erase the contents of the
`svn-process-buffer-name' buffer before commencing.

CMDTYPE is a symbol such as 'mv, 'revert, or 'add, representing the
command to run.

ARGLIST is a list of arguments \(which must include the command name,
for example: '(\"revert\" \"file1\"\)
ARGLIST is flattened and any every nil value is discarded.

If the variable `svn-status-edit-svn-command' is non-nil then the user
can edit ARGLIST before running svn.

The hook svn-pre-run-hook allows to monitor/modify the ARGLIST."
  (setq arglist (svn-status-flatten-list arglist))
  (if (eq (process-status "svn") nil)
      (progn
        (when svn-status-edit-svn-command
          (setq arglist (append
                         (list (car arglist))
                         (split-string
                          (read-from-minibuffer
                           (format "svn %s flags: " (car arglist))
                           (mapconcat 'identity (cdr arglist) " ")))))
          (when (eq svn-status-edit-svn-command t)
            (svn-status-toggle-edit-cmd-flag t))
          (message "svn-run %s: %S" cmdtype arglist))
        (run-hooks 'svn-pre-run-hook)
        (unless (eq mode-line-process 'svn-status-mode-line-process)
          (setq svn-pre-run-mode-line-process mode-line-process)
          (setq mode-line-process 'svn-status-mode-line-process))
        (setq svn-status-pre-run-svn-buffer (current-buffer))
        (let* ((proc-buf (get-buffer-create svn-process-buffer-name))
               (svn-exe svn-status-svn-executable)
               (svn-proc))
          (when (listp (car arglist))
            (setq arglist (car arglist)))
          (save-excursion
            (set-buffer proc-buf)
            (unless (file-executable-p default-directory)
              (message "psvn: workaround in %s needed: %s no longer exists" (current-buffer) default-directory)
              (cd (expand-file-name "~")))
            (setq buffer-read-only nil)
            (buffer-disable-undo)
            (fundamental-mode)
            (if clear-process-buffer
                (delete-region (point-min) (point-max))
              (goto-char (point-max)))
            (setq svn-process-cmd cmdtype)
            (setq svn-status-last-commit-author nil)
            (setq svn-status-mode-line-process-status (format " running %s" cmdtype))
            (svn-status-update-mode-line)
            (sit-for 0.1)
            (ring-insert svn-last-cmd-ring (list (current-time-string) arglist default-directory))
            (if run-asynchron
                (progn
                  ;;(message "running asynchron: %s %S" svn-exe arglist)
                  (setq svn-pre-run-asynch-recent-keys (recent-keys))
                  (let ((process-environment (svn-process-environment))
                        (process-connection-type nil))
                    ;; Communicate with the subprocess via pipes rather
                    ;; than via a pseudoterminal, so that if the svn+ssh
                    ;; scheme is being used, SSH will not ask for a
                    ;; passphrase via stdio; psvn.el is currently unable
                    ;; to answer such prompts.  Instead, SSH will run
                    ;; x11-ssh-askpass if possible.  If Emacs is being
                    ;; run on a TTY without $DISPLAY, this will fail; in
                    ;; such cases, the user should start ssh-agent and
                    ;; then run ssh-add explicitly.
                    (setq svn-proc (apply svn-start-process-function "svn" proc-buf svn-exe arglist)))
                  (when svn-status-svn-process-coding-system
                    (set-process-coding-system svn-proc svn-status-svn-process-coding-system
                                               svn-status-svn-process-coding-system))
                  (set-process-sentinel svn-proc 'svn-process-sentinel)
                  (when svn-status-track-user-input
                    (set-process-filter svn-proc 'svn-process-filter)))
              ;;(message "running synchron: %s %S" svn-exe arglist)
              (let ((process-environment (svn-process-environment)))
                ;; `call-process' ignores `process-connection-type' and
                ;; never opens a pseudoterminal.
                (apply svn-call-process-function svn-exe nil proc-buf nil arglist))
              (setq svn-status-last-output-buffer-name svn-process-buffer-name)
              (run-hooks 'svn-post-process-svn-output-hook)
              (setq svn-status-mode-line-process-status "")
              (svn-status-update-mode-line)
              (when svn-pre-run-mode-line-process
                (setq mode-line-process svn-pre-run-mode-line-process)
                (setq svn-pre-run-mode-line-process nil))))))
    (error "You can only run one svn process at once!")))

(defun svn-process-sentinel-fixup-path-seperators ()
    "Convert all path separators to UNIX style.
\(This is a no-op unless `system-type' is windows-nt\)"
  (when (eq system-type 'windows-nt)
      (save-excursion
        (goto-char (point-min))
        (while (search-forward "\\" nil t)
          (replace-match "/")))))

(defun svn-process-sentinel (process event)
  ;;(princ (format "Process: %s had the event `%s'" process event)))
  ;;(save-excursion
  (let ((act-buf (current-buffer)))
    (when svn-pre-run-mode-line-process
      (with-current-buffer svn-status-pre-run-svn-buffer
        (setq mode-line-process svn-pre-run-mode-line-process))
      (setq svn-pre-run-mode-line-process nil))
    (set-buffer (process-buffer process))
    (setq svn-status-mode-line-process-status "")
    (svn-status-update-mode-line)
    (cond ((string= event "finished\n")
           (run-hooks 'svn-post-process-svn-output-hook)
           (cond ((eq svn-process-cmd 'status)
                  ;;(message "svn status finished")
                  (svn-process-sentinel-fixup-path-seperators)
                  (svn-parse-status-result)
                  (svn-status-apply-elide-list)
                  (when svn-status-update-previous-process-output
                    (set-buffer (process-buffer process))
                    (delete-region (point-min) (point-max))
                    (insert "Output from svn command:\n")
                    (insert svn-status-update-previous-process-output)
                    (goto-char (point-min))
                    (setq svn-status-update-previous-process-output nil))
                  (when svn-status-update-list
                    ;; (message "Using svn-status-update-list: %S" svn-status-update-list)
                    (save-excursion
                      (svn-status-update-with-command-list svn-status-update-list))
                    (setq svn-status-update-list nil))
                  (when svn-status-display-new-status-buffer
                    (set-window-configuration svn-status-initial-window-configuration)
                    (if (svn-had-user-input-since-asynch-run)
                        (message "svn status finished")
                      (switch-to-buffer svn-status-buffer-name))))
                 ((eq svn-process-cmd 'log)
                  (svn-status-show-process-output 'log t)
                  (pop-to-buffer svn-status-last-output-buffer-name)
                  (svn-log-view-mode)
                  (forward-line 2)
                  (unless (looking-at "Changed paths:")
                    (forward-line 1))
                  (font-lock-fontify-buffer)
                  (message "svn log finished"))
                 ((eq svn-process-cmd 'info)
                  (svn-status-show-process-output 'info t)
                  (message "svn info finished"))
                 ((eq svn-process-cmd 'ls)
                  (svn-status-show-process-output 'info t)
                  (message "svn ls finished"))
                 ((eq svn-process-cmd 'diff)
                  (svn-status-activate-diff-mode)
                  (message "svn diff finished"))
                 ((eq svn-process-cmd 'parse-info)
                  (svn-status-parse-info-result))
                 ((eq svn-process-cmd 'blame)
                  (svn-status-show-process-output 'blame t)
                  (when svn-status-pre-run-svn-buffer
                    (with-current-buffer svn-status-pre-run-svn-buffer
                      (unless (eq major-mode 'svn-status-mode)
                        (let ((src-line-number (svn-line-number-at-pos)))
                          (pop-to-buffer (get-buffer svn-status-last-output-buffer-name))
                          (goto-line src-line-number)))))
                  (with-current-buffer (get-buffer svn-status-last-output-buffer-name)
                    (svn-status-activate-blame-mode))
                  (message "svn blame finished"))
                 ((eq svn-process-cmd 'commit)
                  (svn-process-sentinel-fixup-path-seperators)
                  (svn-status-remove-temp-file-maybe)
                  (when (member 'commit svn-status-unmark-files-after-list)
                    (svn-status-unset-all-usermarks))
                  (svn-status-update-with-command-list (svn-status-parse-commit-output))
                  (svn-revert-some-buffers)
                  (run-hooks 'svn-log-edit-done-hook)
                  (setq svn-status-files-to-commit nil
                        svn-status-recursive-commit nil)
                  (if (null svn-status-commit-rev-number)
                      (message "No revision to commit.")
                    (message "svn: Committed revision %s." svn-status-commit-rev-number)))
                 ((eq svn-process-cmd 'update)
                  (svn-status-show-process-output 'update t)
                  (setq svn-status-update-list (svn-status-parse-update-output))
                  (svn-revert-some-buffers)
                  (svn-status-update)
                  (if (car svn-status-update-rev-number)
                      (message "svn: Updated to revision %s." (cadr svn-status-update-rev-number))
                    (message "svn: At revision %s." (cadr svn-status-update-rev-number))))
                 ((eq svn-process-cmd 'add)
                  (svn-status-update-with-command-list (svn-status-parse-ar-output))
                  (message "svn add finished"))
                 ((eq svn-process-cmd 'lock)
                  (svn-status-update)
                  (message "svn lock finished"))
                 ((eq svn-process-cmd 'unlock)
                  (svn-status-update)
                  (message "svn unlock finished"))
                 ((eq svn-process-cmd 'mkdir)
                  (svn-status-update)
                  (message "svn mkdir finished"))
                 ((eq svn-process-cmd 'revert)
                  (when (member 'revert svn-status-unmark-files-after-list)
                    (svn-status-unset-all-usermarks))
                  (svn-revert-some-buffers)
                  (svn-status-update)
                  (message "svn revert finished"))
                 ((eq svn-process-cmd 'resolved)
                  (svn-status-update)
                  (message "svn resolved finished"))
                 ((eq svn-process-cmd 'rm)
                  (svn-status-update-with-command-list (svn-status-parse-ar-output))
                  (message "svn rm finished"))
                 ((eq svn-process-cmd 'cleanup)
                  (message "svn cleanup finished"))
                 ((eq svn-process-cmd 'proplist)
                  (svn-status-show-process-output 'proplist t)
                  (message "svn proplist finished"))
                 ((eq svn-process-cmd 'checkout)
                  (svn-status default-directory))
                 ((eq svn-process-cmd 'proplist-parse)
                  (svn-status-property-parse-property-names))
                 ((eq svn-process-cmd 'propset)
                  (svn-status-remove-temp-file-maybe)
                  (if (member svn-status-propedit-property-name '("svn:keywords"))
                      (svn-status-update-with-command-list (svn-status-parse-property-output))
                    (svn-status-update)))
                 ((eq svn-process-cmd 'propdel)
                  (svn-status-update))))
          ((string= event "killed\n")
           (message "svn process killed"))
          ((string-match "exited abnormally" event)
           (while (accept-process-output process 0 100))
           ;; find last error message and show it.
           (goto-char (point-max))
           (if (re-search-backward "^svn: \\(.*\\)" nil t)
               (svn-process-handle-error (match-string 1))
             (message "svn failed: %s" event)))
          (t
           (message "svn process had unknown event: %s" event))
          (svn-status-show-process-output nil t))))

(defvar svn-process-handle-error-msg nil)
(defun svn-process-handle-error (error-msg)
  (let ((svn-process-handle-error-msg error-msg))
    (electric-helpify 'svn-process-help-with-error-msg)))

(defun svn-process-help-with-error-msg ()
  (interactive)
  (let ((help-msg (cadr (assoc svn-process-handle-error-msg
                               '(("Cannot non-recursively commit a directory deletion"
                                  "Please unmark all files and position point at the directory you would like to remove.\nThen run commit again."))))))
    (if help-msg
        (save-excursion
          (with-output-to-temp-buffer (help-buffer)
            (princ (format "svn failed: %s\n\n%s" svn-process-handle-error-msg help-msg))))
      (message "svn failed: %s" svn-process-handle-error-msg))))


(defun svn-process-filter (process str)
  "Track the svn process output and ask user questions in the minibuffer when appropriate."
  (save-window-excursion
    (set-buffer svn-process-buffer-name)
    ;;(message "svn-process-filter: %s" str)
    (goto-char (point-max))
    (insert str)
    (save-excursion
      (goto-char (svn-point-at-bol))
      (when (looking-at "Password for '\\(.+\\)': ")
        ;(svn-status-show-process-buffer)
        (let ((passwd (read-passwd
                       (format "Enter svn password for %s: " (match-string 1)))))
          (svn-process-send-string-and-newline passwd t)))
      (when (looking-at "Username: ")
        (let ((user-name (read-string "Username for svn operation: ")))
          (svn-process-send-string-and-newline user-name)))
      (when (looking-at "(R)eject, accept (t)emporarily or accept (p)ermanently")
        (svn-status-show-process-buffer)
        (let ((answer (read-string "(R)eject, accept (t)emporarily or accept (p)ermanently? ")))
          (svn-process-send-string (substring answer 0 1)))))))

(defun svn-revert-some-buffers (&optional tree)
  "Reverts all buffers visiting a file in TREE that aren't modified.
To be run after a commit, an update or a merge."
  (interactive)
  (let ((tree (or (svn-status-base-dir) tree)))
    (dolist (buffer (buffer-list))
      (with-current-buffer buffer
        (when (not (buffer-modified-p))
          (let ((file (buffer-file-name)))
            (when file
              (let ((root (svn-status-base-dir (file-name-directory file)))
                    (point-pos (point)))
                (when (and root
                           (string= root tree)
                           ;; buffer is modified and in the tree TREE.
                           svn-status-auto-revert-buffers)
                  (when svn-status-fancy-file-state-in-modeline
                    (svn-status-update-modeline))
                  ;; (message "svn-revert-some-buffers: %s %s" (buffer-file-name) (verify-visited-file-modtime (current-buffer)))
                  ;; Keep the buffer if the file doesn't exist
                  (when (and (file-exists-p file) (not (verify-visited-file-modtime (current-buffer))))
                    (revert-buffer t t)
                    (goto-char point-pos)))))))))))

(defun svn-parse-rev-num (str)
  (if (and str (stringp str)
           (save-match-data (string-match "^[0-9]+" str)))
      (string-to-number str)
    -1))

(defsubst svn-status-make-ui-status ()
  "Make a ui-status structure for a file in a svn working copy.
The initial values in the structure returned by this function
are good for a file or directory that the user hasn't seen before.

The ui-status structure keeps track of how the file or directory
should be displayed in svn-status mode.  Updating the svn-status
buffer from the working copy preserves the ui-status if possible.
User commands modify this structure; each file or directory must
thus have its own copy.

Currently, the ui-status is a list (USER-MARK USER-ELIDE).
USER-MARK is non-nil iff the user has marked the file or directory,
  typically with `svn-status-set-user-mark'.  To read USER-MARK,
  call `svn-status-line-info->has-usermark'.
USER-ELIDE is non-nil iff the user has elided the file or directory
  from the svn-status buffer, typically with `svn-status-toggle-elide'.
  To read USER-ELIDE, call `svn-status-line-info->user-elide'.

Call `svn-status-line-info->ui-status' to access the whole ui-status
structure."
  (list nil nil))

(defun svn-status-make-dummy-dirs (dir-list old-ui-information)
  "Calculate additionally necessary directories that were not shown in the output
of 'svn status'"
  ;; (message "svn-status-make-dummy-dirs %S" dir-list)
  (let ((candidate)
        (base-dir))
    (dolist (dir dir-list)
      (setq base-dir (file-name-directory dir))
      (while base-dir
        ;;(message "dir: %S dir-list: %S, base-dir: %S" dir dir-list base-dir)
        (setq candidate (replace-regexp-in-string "/+$" "" base-dir))
        (setq base-dir (file-name-directory candidate))
        ;; (message "dir: %S, candidate: %S" dir candidate)
        (add-to-list 'dir-list candidate))))
  ;; (message "svn-status-make-dummy-dirs %S" dir-list)
  (append (mapcar (lambda (dir)
                    (svn-status-make-line-info
                     dir
                     (gethash dir old-ui-information)))
                  dir-list)
          svn-status-info))

(defun svn-status-make-line-info (&optional
                                  path
                                  ui
                                  file-mark prop-mark
                                  local-rev last-change-rev
                                  author
                                  update-mark
                                  locked-mark
                                  with-history-mark
                                  switched-mark
                                  locked-repo-mark
                                  psvn-extra-info)
  "Create a new line-info from the given arguments
Anything left nil gets a sensible default.
nb: LOCKED-MARK refers to the kind of locks you get after an error,
    LOCKED-REPO-MARK is the kind managed with `svn lock'"
  (list (or ui (svn-status-make-ui-status))
        (or file-mark ? )
        (or prop-mark ? )
        (or path "")
        (or local-rev ? )
        (or last-change-rev ? )
        (or author "")
        update-mark
        locked-mark
        with-history-mark
        switched-mark
        locked-repo-mark
        psvn-extra-info))

(defvar svn-user-names-including-blanks nil "A list of svn user names that include blanks.
To add support for the names \"feng shui\" and \"mister blank\", place the following in your .emacs:
 (setq svn-user-names-including-blanks '(\"feng shui\" \"mister blank\"))
 (add-hook 'svn-pre-parse-status-hook 'svn-status-parse-fixup-user-names-including-blanks)
")
;;(setq svn-user-names-including-blanks '("feng shui" "mister blank"))
;;(add-hook 'svn-pre-parse-status-hook 'svn-status-parse-fixup-user-names-including-blanks)

(defun svn-status-parse-fixup-user-names-including-blanks ()
  "Helper function to allow user names that include blanks.
Add this function to the `svn-pre-parse-status-hook'. The variable
`svn-user-names-including-blanks' must be configured to hold all user names that contain
blanks. This function replaces the blanks with '-' to allow further processing with
the usual parsing functionality in `svn-parse-status-result'."
  (when svn-user-names-including-blanks
    (goto-char (point-min))
    (let ((search-string (concat " \\(" (mapconcat 'concat svn-user-names-including-blanks "\\|") "\\) ")))
      (save-match-data
        (save-excursion
          (while (re-search-forward search-string (point-max) t)
            (replace-match (replace-regexp-in-string " " "-" (match-string 1)) nil nil nil 1)))))))

(defun svn-parse-status-result ()
  "Parse the `svn-process-buffer-name' buffer.
The results are used to build the `svn-status-info' variable."
  (setq svn-status-head-revision nil)
  (save-excursion
    (let ((old-ui-information (svn-status-ui-information-hash-table))
          (svn-marks)
          (svn-file-mark)
          (svn-property-mark)
          (svn-wc-locked-mark)
          (svn-repo-locked-mark)
          (svn-with-history-mark)
          (svn-switched-mark)
          (svn-update-mark)
          (local-rev)
          (last-change-rev)
          (author)
          (path)
          (dir)
          (revision-width svn-status-default-revision-width)
          (author-width svn-status-default-author-width)
          (svn-marks-length (if svn-status-verbose
                                (if svn-status-remote
                                    8 6)
                              (if svn-status-remote
                                  ;; not verbose
                                  8 7)))
          (dir-set '("."))
          (externals-map (make-hash-table :test 'equal))
          (skip-double-external-dir-entry-name nil))
      (set-buffer svn-process-buffer-name)
      (setq svn-status-info nil)
      (run-hooks 'svn-pre-parse-status-hook)
      (goto-char (point-min))
      (while (< (point) (point-max))
        (cond
         ((= (svn-point-at-eol) (svn-point-at-bol)) ;skip blank lines
          nil)
         ((looking-at "Status against revision:[ ]+\\([0-9]+\\)")
          ;; the above message appears for the main listing plus once for each svn:externals entry
          (unless svn-status-head-revision
            (setq svn-status-head-revision (match-string 1))))
         ((looking-at "Performing status on external item at '\\(.*\\)'")
          ;; The *next* line has info about the directory named in svn:externals
          ;; [ie the directory in (match-string 1)]
          ;; we should parse it, and merge the info with what we have already know
          ;; but for now just ignore the line completely
          ; (forward-line)
          ;;  Actually, this seems to not always be the case
          ;;  I have an example where we are in an svn:external which
          ;;  is itself inside a svn:external, this need not be true:
          ;;  the next line is not 'X dir' but just 'dir', so we
          ;;  actually need to parse that line, or the results will
          ;;  not contain dir!
          ;; so we should merge lines 'X dir' with ' dir', but for now
          ;; we just leave both in the results

          ;; My attempt to merge the lines uses skip-double-external-dir-entry-name
          ;; and externals-map
          (setq skip-double-external-dir-entry-name (svn-match-string-no-properties 1))
          ;; (message "Going to skip %s" skip-double-external-dir-entry-name)
          nil)
         ((looking-at "--- Changelist") ; skip svn changelist header lines
          ;; See: http://svn.collab.net/repos/svn/trunk/notes/changelist-design.txt
          nil)
         (t
          (setq svn-marks (buffer-substring (point) (+ (point) svn-marks-length))
                svn-file-mark (elt svn-marks 0)         ; 1st column - M,A,C,D,G,? etc
                svn-property-mark (elt svn-marks 1)     ; 2nd column - M,C (properties)
                svn-wc-locked-mark (elt svn-marks 2)    ; 3rd column - L or blank
                svn-with-history-mark (elt svn-marks 3) ; 4th column - + or blank
                svn-switched-mark (elt svn-marks 4)     ; 5th column - S or blank
                svn-repo-locked-mark (elt svn-marks 5)) ; 6th column - K,O,T,B or blank
          (when svn-status-remote
              (setq svn-update-mark (elt svn-marks 7))) ; 8th column - * or blank
          (when (eq svn-property-mark ?\ )     (setq svn-property-mark nil))
          (when (eq svn-wc-locked-mark ?\ )    (setq svn-wc-locked-mark nil))
          (when (eq svn-with-history-mark ?\ ) (setq svn-with-history-mark nil))
          (when (eq svn-switched-mark ?\ )     (setq svn-switched-mark nil))
          (when (eq svn-update-mark ?\ )       (setq svn-update-mark nil))
          (when (eq svn-repo-locked-mark ?\ )  (setq svn-repo-locked-mark nil))
          (forward-char svn-marks-length)
          (skip-chars-forward " ")
          ;; (message "after marks: '%s'" (buffer-substring (point) (line-end-position)))
          (cond
           ((looking-at "\\([-?]\\|[0-9]+\\) +\\([-?]\\|[0-9]+\\) +\\([^ ]+\\) *\\(.+\\)$")
            (setq local-rev (svn-parse-rev-num (match-string 1))
                  last-change-rev (svn-parse-rev-num (match-string 2))
                  author (match-string 3)
                  path (match-string 4)))
           ((looking-at "\\([-?]\\|[0-9]+\\) +\\([^ ]+\\)$")
            (setq local-rev (svn-parse-rev-num (match-string 1))
                  last-change-rev -1
                  author "?"
                  path (match-string 2)))
           ((looking-at "\\(.*\\)")
            (setq path (match-string 1)
                  local-rev -1
                  last-change-rev -1
                  author (if (eq svn-file-mark ?X) "" "?"))) ;clear author of svn:externals dirs
           (t
            (error "Unknown status line format")))
          (unless path (setq path "."))
          (setq dir (file-name-directory path))
          (if (and (not svn-status-verbose) dir)
              (let ((dirname (directory-file-name dir)))
                (if (not (member dirname dir-set))
                    (setq dir-set (cons dirname dir-set)))))
          (if (and skip-double-external-dir-entry-name (string= skip-double-external-dir-entry-name path))
              ;; merge this entry to a previous saved one
              (let ((info (gethash path externals-map)))
                ;; (message "skip-double-external-dir-entry-name: %s - path: %s" skip-double-external-dir-entry-name path)
                (if info
                    (progn
                      (svn-status-line-info->set-localrev info local-rev)
                      (svn-status-line-info->set-lastchangerev info last-change-rev)
                      (svn-status-line-info->set-author info author)
                      (svn-status-message 3 "merging entry for %s to %s" path info)
                      (setq skip-double-external-dir-entry-name nil))
                  (message "psvn: %s not handled correct, please report this case." path)))
            (setq svn-status-info
                  (cons (svn-status-make-line-info path
                                                   (gethash path old-ui-information)
                                                   svn-file-mark
                                                   svn-property-mark
                                                   local-rev
                                                   last-change-rev
                                                   author
                                                   svn-update-mark
                                                   svn-wc-locked-mark
                                                   svn-with-history-mark
                                                   svn-switched-mark
                                                   svn-repo-locked-mark
                                                   nil) ;;psvn-extra-info
                        svn-status-info)))
          (when (eq svn-file-mark ?X)
            (svn-puthash (match-string 1) (car svn-status-info) externals-map)
            (svn-status-message 3 "found external: %s %S" (match-string 1) (car svn-status-info)))
          (setq revision-width (max revision-width
                                    (length (number-to-string local-rev))
                                    (length (number-to-string last-change-rev))))
          (setq author-width (max author-width (length author)))))
        (forward-line 1))
      (unless svn-status-verbose
        (setq svn-status-info (svn-status-make-dummy-dirs dir-set
                                                          old-ui-information)))
      (setq svn-status-default-column
            (+ 6 revision-width revision-width author-width
               (if svn-status-short-mod-flag-p 3 0)))
      (setq svn-status-line-format (format " %%c%%c%%c %%%ds %%%ds %%-%ds"
                                           revision-width
                                           revision-width
                                           author-width))
      (setq svn-status-info (nreverse svn-status-info))
      (when svn-status-sort-status-buffer
        (setq svn-status-info (sort svn-status-info 'svn-status-sort-predicate))))))

;;(string-lessp "." "%") => nil
;(svn-status-sort-predicate '(t t t ".") '(t t t "%")) => t
(defun svn-status-sort-predicate (a b)
  "Return t if A should appear before B in the `svn-status-buffer-name' buffer.
A and B must be line-info's."
  (string-lessp (concat (svn-status-line-info->full-path a) "/")
                (concat (svn-status-line-info->full-path b) "/")))

(defun svn-status-remove-temp-file-maybe ()
  "Remove any (no longer required) temporary files created by psvn.el."
  (when svn-status-temp-file-to-remove
    (when (file-exists-p svn-status-temp-file-to-remove)
      (delete-file svn-status-temp-file-to-remove))
    (when (file-exists-p svn-status-temp-arg-file)
      (delete-file svn-status-temp-arg-file))
    (setq svn-status-temp-file-to-remove nil)))

(defun svn-status-remove-control-M ()
  "Remove ^M at end of line in the whole buffer."
  (interactive)
  (let ((buffer-read-only nil))
    (save-match-data
      (save-excursion
        (goto-char (point-min))
        (while (re-search-forward "\r$" (point-max) t)
          (replace-match "" nil nil))))))

(condition-case nil
    ;;(easy-menu-add-item nil '("tools") ["SVN Status" svn-status t] "PCL-CVS")
    (easy-menu-add-item nil '("tools") ["SVN Status" svn-status t])
  (error (message "psvn: could not install menu")))

(defvar svn-status-mode-map () "Keymap used in `svn-status-mode' buffers.")
(put 'svn-status-mode-map 'risky-local-variable t) ;for Emacs 20.7
(defvar svn-status-mode-mark-map ()
  "Subkeymap used in `svn-status-mode' for mark commands.")
(put 'svn-status-mode-mark-map      'risky-local-variable t) ;for Emacs 20.7
(defvar svn-status-mode-property-map ()
  "Subkeymap used in `svn-status-mode' for property commands.")
(put 'svn-status-mode-property-map  'risky-local-variable t) ;for Emacs 20.7
(defvar svn-status-mode-options-map ()
  "Subkeymap used in `svn-status-mode' for option commands.")
(put 'svn-status-mode-options-map   'risky-local-variable t) ;for Emacs 20.7
(defvar svn-status-mode-trac-map ()
  "Subkeymap used in `svn-status-mode' for trac issue tracker commands.")
(put 'svn-status-mode-trac-map      'risky-local-variable t) ;for Emacs 20.7
(defvar svn-status-mode-extension-map ()
  "Subkeymap used in `svn-status-mode' for some seldom used commands.")
(put 'svn-status-mode-extension-map 'risky-local-variable t) ;for Emacs 20.7
(defvar svn-status-mode-branch-map ()
  "Subkeymap used in `svn-status-mode' for branching commands.")
(put 'svn-status-mode-extension-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-status-mode-map)
  (setq svn-status-mode-map (make-sparse-keymap))
  (suppress-keymap svn-status-mode-map)
  ;; Don't use (kbd "<return>"); it's unreachable with GNU Emacs 21.3 on a TTY.
  (define-key svn-status-mode-map (kbd "RET") 'svn-status-find-file-or-examine-directory)
  (define-key svn-status-mode-map (kbd "<mouse-2>") 'svn-status-mouse-find-file-or-examine-directory)
  (define-key svn-status-mode-map (kbd "^") 'svn-status-examine-parent)
  (define-key svn-status-mode-map (kbd "s") 'svn-status-show-process-buffer)
  (define-key svn-status-mode-map (kbd "h") 'svn-status-pop-to-partner-buffer)
  (define-key svn-status-mode-map (kbd "f") 'svn-status-find-files)
  (define-key svn-status-mode-map (kbd "o") 'svn-status-find-file-other-window)
  (define-key svn-status-mode-map (kbd "C-o") 'svn-status-find-file-other-window-noselect)
  (define-key svn-status-mode-map (kbd "v") 'svn-status-view-file-other-window)
  (define-key svn-status-mode-map (kbd "e") 'svn-status-toggle-edit-cmd-flag)
  (define-key svn-status-mode-map (kbd "g") 'svn-status-update)
  (define-key svn-status-mode-map (kbd "M-s") 'svn-status-update) ;; PCL-CVS compatibility
  (define-key svn-status-mode-map (kbd "q") 'svn-status-bury-buffer)
  (define-key svn-status-mode-map (kbd "x") 'svn-status-redraw-status-buffer)
  (define-key svn-status-mode-map (kbd "H") 'svn-status-use-history)
  (define-key svn-status-mode-map (kbd "m") 'svn-status-set-user-mark)
  (define-key svn-status-mode-map (kbd "u") 'svn-status-unset-user-mark)
  ;; This matches a binding of `dired-unmark-all-files' in `dired-mode-map'
  ;; of both GNU Emacs and XEmacs.  It seems unreachable with XEmacs on
  ;; TTY, but if that's a problem then its Dired needs fixing too.
  ;; Or you could just use "*!".
  (define-key svn-status-mode-map "\M-\C-?" 'svn-status-unset-all-usermarks)
  ;; The key that normally deletes characters backwards should here
  ;; instead unmark files backwards.  In GNU Emacs, that would be (kbd
  ;; "DEL") aka [?\177], but XEmacs treats those as [(delete)] and
  ;; would bind a key that normally deletes forwards.  [(backspace)]
  ;; is unreachable with GNU Emacs on a tty.  Try to recognize the
  ;; dialect and act accordingly.
  ;;
  ;; XEmacs has a `delete-forward-p' function that checks the
  ;; `delete-key-deletes-forward' option.  We don't use those, for two
  ;; reasons: psvn.el may be loaded before user customizations, and
  ;; XEmacs allows simultaneous connections to multiple devices with
  ;; different keyboards.
  (define-key svn-status-mode-map
              (if (member (kbd "DEL") '([(delete)] [delete]))
                  [(backspace)]         ; XEmacs
                (kbd "DEL"))            ; GNU Emacs
              'svn-status-unset-user-mark-backwards)
  (define-key svn-status-mode-map (kbd "$") 'svn-status-toggle-elide)
  (define-key svn-status-mode-map (kbd "w") 'svn-status-copy-current-line-info)
  (define-key svn-status-mode-map (kbd ".") 'svn-status-goto-root-or-return)
  (define-key svn-status-mode-map (kbd "I") 'svn-status-parse-info)
  (define-key svn-status-mode-map (kbd "V") 'svn-status-svnversion)
  (define-key svn-status-mode-map (kbd "?") 'svn-status-toggle-hide-unknown)
  (define-key svn-status-mode-map (kbd "_") 'svn-status-toggle-hide-unmodified)
  (define-key svn-status-mode-map (kbd "a") 'svn-status-add-file)
  (define-key svn-status-mode-map (kbd "A") 'svn-status-add-file-recursively)
  (define-key svn-status-mode-map (kbd "+") 'svn-status-make-directory)
  (define-key svn-status-mode-map (kbd "R") 'svn-status-mv)
  (define-key svn-status-mode-map (kbd "C") 'svn-status-cp)
  (define-key svn-status-mode-map (kbd "D") 'svn-status-rm)
  (define-key svn-status-mode-map (kbd "c") 'svn-status-commit)
  (define-key svn-status-mode-map (kbd "M-c") 'svn-status-cleanup)
  (define-key svn-status-mode-map (kbd "k") 'svn-status-lock)
  (define-key svn-status-mode-map (kbd "K") 'svn-status-unlock)
  (define-key svn-status-mode-map (kbd "U") 'svn-status-update-cmd)
  (define-key svn-status-mode-map (kbd "M-u") 'svn-status-update-cmd)
  (define-key svn-status-mode-map (kbd "r") 'svn-status-revert)
  (define-key svn-status-mode-map (kbd "l") 'svn-status-show-svn-log)
  (define-key svn-status-mode-map (kbd "i") 'svn-status-info)
  (define-key svn-status-mode-map (kbd "b") 'svn-status-blame)
  (define-key svn-status-mode-map (kbd "=") 'svn-status-show-svn-diff)
  ;; [(control ?=)] is unreachable on TTY, but you can use "*u" instead.
  ;; (Is the "u" mnemonic for something?)
  (define-key svn-status-mode-map (kbd "C-=") 'svn-status-show-svn-diff-for-marked-files)
  (define-key svn-status-mode-map (kbd "~") 'svn-status-get-specific-revision)
  (define-key svn-status-mode-map (kbd "E") 'svn-status-ediff-with-revision)

  (define-key svn-status-mode-map (kbd "S g") 'svn-status-grep-files)
  (define-key svn-status-mode-map (kbd "S s") 'svn-status-search-files)

  (define-key svn-status-mode-map (kbd "n") 'svn-status-next-line)
  (define-key svn-status-mode-map (kbd "p") 'svn-status-previous-line)
  (define-key svn-status-mode-map (kbd "<down>") 'svn-status-next-line)
  (define-key svn-status-mode-map (kbd "<up>") 'svn-status-previous-line)
  (define-key svn-status-mode-map (kbd "C-x C-j") 'svn-status-dired-jump)
  (define-key svn-status-mode-map [down-mouse-3] 'svn-status-popup-menu)
  (setq svn-status-mode-mark-map (make-sparse-keymap))
  (define-key svn-status-mode-map (kbd "*") svn-status-mode-mark-map)
  (define-key svn-status-mode-mark-map (kbd "!") 'svn-status-unset-all-usermarks)
  (define-key svn-status-mode-mark-map (kbd "?") 'svn-status-mark-unknown)
  (define-key svn-status-mode-mark-map (kbd "A") 'svn-status-mark-added)
  (define-key svn-status-mode-mark-map (kbd "M") 'svn-status-mark-modified)
  (define-key svn-status-mode-mark-map (kbd "P") 'svn-status-mark-modified-properties)
  (define-key svn-status-mode-mark-map (kbd "D") 'svn-status-mark-deleted)
  (define-key svn-status-mode-mark-map (kbd "*") 'svn-status-mark-changed)
  (define-key svn-status-mode-mark-map (kbd ".") 'svn-status-mark-by-file-ext)
  (define-key svn-status-mode-mark-map (kbd "%") 'svn-status-mark-filename-regexp)
  (define-key svn-status-mode-mark-map (kbd "u") 'svn-status-show-svn-diff-for-marked-files))
(when (not svn-status-mode-property-map)
  (setq svn-status-mode-property-map (make-sparse-keymap))
  (define-key svn-status-mode-property-map (kbd "l") 'svn-status-property-list)
  (define-key svn-status-mode-property-map (kbd "s") 'svn-status-property-set)
  (define-key svn-status-mode-property-map (kbd "d") 'svn-status-property-delete)
  (define-key svn-status-mode-property-map (kbd "e") 'svn-status-property-edit-one-entry)
  (define-key svn-status-mode-property-map (kbd "i") 'svn-status-property-ignore-file)
  (define-key svn-status-mode-property-map (kbd "I") 'svn-status-property-ignore-file-extension)
  ;; XEmacs 21.4.15 on TTY (vt420) converts `C-i' to `TAB',
  ;; which [(control ?i)] won't match.  Handle it separately.
  ;; On GNU Emacs, the following two forms bind the same key,
  ;; reducing clutter in `where-is'.
  (define-key svn-status-mode-property-map [(control ?i)] 'svn-status-property-edit-svn-ignore)
  (define-key svn-status-mode-property-map (kbd "TAB") 'svn-status-property-edit-svn-ignore)
  (define-key svn-status-mode-property-map (kbd "k") 'svn-status-property-set-keyword-list)
  (define-key svn-status-mode-property-map (kbd "Ki") 'svn-status-property-set-keyword-id)
  (define-key svn-status-mode-property-map (kbd "Kd") 'svn-status-property-set-keyword-date)
  (define-key svn-status-mode-property-map (kbd "y") 'svn-status-property-set-eol-style)
  (define-key svn-status-mode-property-map (kbd "x") 'svn-status-property-set-executable)
  (define-key svn-status-mode-property-map (kbd "m") 'svn-status-property-set-mime-type)
  ;; TODO: Why is `svn-status-select-line' in `svn-status-mode-property-map'?
  (define-key svn-status-mode-property-map (kbd "RET") 'svn-status-select-line)
  (define-key svn-status-mode-map (kbd "P") svn-status-mode-property-map))
(when (not svn-status-mode-extension-map)
  (setq svn-status-mode-extension-map (make-sparse-keymap))
  (define-key svn-status-mode-extension-map (kbd "v") 'svn-status-resolved)
  (define-key svn-status-mode-extension-map (kbd "X") 'svn-status-resolve-conflicts)
  (define-key svn-status-mode-extension-map (kbd "e") 'svn-status-export)
  (define-key svn-status-mode-map (kbd "X") svn-status-mode-extension-map))
(when (not svn-status-mode-options-map)
  (setq svn-status-mode-options-map (make-sparse-keymap))
  (define-key svn-status-mode-options-map (kbd "s") 'svn-status-save-state)
  (define-key svn-status-mode-options-map (kbd "l") 'svn-status-load-state)
  (define-key svn-status-mode-options-map (kbd "x") 'svn-status-toggle-sort-status-buffer)
  (define-key svn-status-mode-options-map (kbd "v") 'svn-status-toggle-svn-verbose-flag)
  (define-key svn-status-mode-options-map (kbd "f") 'svn-status-toggle-display-full-path)
  (define-key svn-status-mode-options-map (kbd "t") 'svn-status-set-trac-project-root)
  (define-key svn-status-mode-options-map (kbd "n") 'svn-status-set-module-name)
  (define-key svn-status-mode-options-map (kbd "c") 'svn-status-set-changelog-style)
  (define-key svn-status-mode-options-map (kbd "b") 'svn-status-set-branch-list)
  (define-key svn-status-mode-map (kbd "O") svn-status-mode-options-map))
(when (not svn-status-mode-trac-map)
  (setq svn-status-mode-trac-map (make-sparse-keymap))
  (define-key svn-status-mode-trac-map (kbd "w") 'svn-trac-browse-wiki)
  (define-key svn-status-mode-trac-map (kbd "t") 'svn-trac-browse-timeline)
  (define-key svn-status-mode-trac-map (kbd "m") 'svn-trac-browse-roadmap)
  (define-key svn-status-mode-trac-map (kbd "r") 'svn-trac-browse-report)
  (define-key svn-status-mode-trac-map (kbd "s") 'svn-trac-browse-source)
  (define-key svn-status-mode-trac-map (kbd "i") 'svn-trac-browse-ticket)
  (define-key svn-status-mode-trac-map (kbd "c") 'svn-trac-browse-changeset)
  (define-key svn-status-mode-map (kbd "T") svn-status-mode-trac-map))
(when (not svn-status-mode-branch-map)
  (setq svn-status-mode-branch-map (make-sparse-keymap))
  (define-key svn-status-mode-branch-map (kbd "d") 'svn-branch-diff)
  (define-key svn-status-mode-map (kbd "B") svn-status-mode-branch-map))

(easy-menu-define svn-status-mode-menu svn-status-mode-map
  "'svn-status-mode' menu"
  '("SVN"
    ["svn status" svn-status-update t]
    ["svn update" svn-status-update-cmd t]
    ["svn commit" svn-status-commit t]
    ["svn log" svn-status-show-svn-log t]
    ["svn info" svn-status-info t]
    ["svn blame" svn-status-blame t]
    ("Diff"
     ["svn diff current file" svn-status-show-svn-diff t]
     ["svn diff marked files" svn-status-show-svn-diff-for-marked-files t]
     ["svn ediff current file" svn-status-ediff-with-revision t]
     ["svn resolve conflicts" svn-status-resolve-conflicts]
     )
    ("Search"
     ["Grep marked files" svn-status-grep-files t]
     ["Search marked files" svn-status-search-files t]
     )
    ["svn cat ..." svn-status-get-specific-revision t]
    ["svn add" svn-status-add-file t]
    ["svn add recursively" svn-status-add-file-recursively t]
    ["svn mkdir..." svn-status-make-directory t]
    ["svn mv..." svn-status-mv t]
    ["svn cp..." svn-status-cp t]
    ["svn rm..." svn-status-rm t]
    ["svn export..." svn-status-export t]
    ["Up Directory" svn-status-examine-parent t]
    ["Elide Directory" svn-status-toggle-elide t]
    ["svn revert" svn-status-revert t]
    ["svn resolved" svn-status-resolved t]
    ["svn cleanup" svn-status-cleanup t]
    ["svn lock" svn-status-lock t]
    ["svn unlock" svn-status-unlock t]
    ["Show Process Buffer" svn-status-show-process-buffer t]
    ("Branch"
     ["diff" svn-branch-diff t]
     ["Set Branch list" svn-status-set-branch-list t]
     )
    ("Property"
     ["svn proplist" svn-status-property-list t]
     ["Set Multiple Properties..." svn-status-property-set t]
     ["Edit One Property..." svn-status-property-edit-one-entry t]
     ["svn propdel..." svn-status-property-delete t]
     "---"
     ["svn:ignore File..." svn-status-property-ignore-file t]
     ["svn:ignore File Extension..." svn-status-property-ignore-file-extension t]
     ["Edit svn:ignore Property" svn-status-property-edit-svn-ignore t]
     "---"
     ["Edit svn:keywords List" svn-status-property-set-keyword-list t]
     ["Add/Remove Id to/from svn:keywords" svn-status-property-set-keyword-id t]
     ["Add/Remove Date to/from svn:keywords" svn-status-property-set-keyword-date t]
     "---"
     ["Select svn:eol-style" svn-status-property-set-eol-style t]
     ["Set svn:executable" svn-status-property-set-executable t]
     ["Set svn:mime-type" svn-status-property-set-mime-type t]
     )
    ("Options"
     ["Save Options" svn-status-save-state t]
     ["Load Options" svn-status-load-state t]
     ["Set Trac project root" svn-status-set-trac-project-root t]
     ["Set Short module name" svn-status-set-module-name t]
     ["Set Changelog style" svn-status-set-changelog-style t]
     ["Set Branch list" svn-status-set-branch-list t]
     ["Sort the *svn-status* buffer" svn-status-toggle-sort-status-buffer
      :style toggle :selected svn-status-sort-status-buffer]
     ["Use -v for svn status calls" svn-status-toggle-svn-verbose-flag
      :style toggle :selected svn-status-verbose]
     ["Display full path names" svn-status-toggle-display-full-path
      :style toggle :selected svn-status-display-full-path]
     )
    ("Trac"
     ["Browse wiki" svn-trac-browse-wiki t]
     ["Browse timeline" svn-trac-browse-timeline t]
     ["Browse roadmap" svn-trac-browse-roadmap t]
     ["Browse source" svn-trac-browse-source t]
     ["Browse report" svn-trac-browse-report t]
     ["Browse ticket" svn-trac-browse-ticket t]
     ["Browse changeset" svn-trac-browse-changeset t]
     ["Set Trac project root" svn-status-set-trac-project-root t]
     )
    "---"
    ["Edit Next SVN Cmd Line" svn-status-toggle-edit-cmd-flag t]
    ["Work Directory History..." svn-status-use-history t]
    ("Mark / Unmark"
     ["Mark" svn-status-set-user-mark t]
     ["Unmark" svn-status-unset-user-mark t]
     ["Unmark all" svn-status-unset-all-usermarks t]
     "---"
     ["Mark/Unmark unknown" svn-status-mark-unknown t]
     ["Mark/Unmark modified" svn-status-mark-modified t]
     ["Mark/Unmark modified properties" svn-status-mark-modified-properties t]
     ["Mark/Unmark added" svn-status-mark-added t]
     ["Mark/Unmark deleted" svn-status-mark-deleted t]
     ["Mark/Unmark modified/added/deleted" svn-status-mark-changed t]
     ["Mark/Unmark filename by extension" svn-status-mark-by-file-ext t]
     ["Mark/Unmark filename by regexp" svn-status-mark-filename-regexp t]
     )
    ["Hide Unknown" svn-status-toggle-hide-unknown
     :style toggle :selected svn-status-hide-unknown]
    ["Hide Unmodified" svn-status-toggle-hide-unmodified
     :style toggle :selected svn-status-hide-unmodified]
    ["Show Client versions" svn-status-version t]
    ["Prepare bug report" svn-prepare-bug-report t]
    ))

(defvar svn-status-file-popup-menu-list
  '(["open" svn-status-find-file-other-window t]
    ["svn diff" svn-status-show-svn-diff t]
    ["svn commit" svn-status-commit t]
    ["svn log" svn-status-show-svn-log t]
    ["svn blame" svn-status-blame t]
    ["mark" svn-status-set-user-mark t]
    ["unmark" svn-status-unset-user-mark t]
    ["svn add" svn-status-add-file t]
    ["svn add recursively" svn-status-add-file-recursively t]
    ["svn mv..." svn-status-mv t]
    ["svn rm..." svn-status-rm t]
    ["svn lock" svn-status-lock t]
    ["svn unlock" svn-status-unlock t]
    ["svn info" svn-status-info t]
    ) "A list of menu entries for `svn-status-popup-menu'")

;; extend svn-status-file-popup-menu-list via:
;; (add-to-list 'svn-status-file-popup-menu-list ["commit" svn-status-commit t])

(defun svn-status-popup-menu (event)
  "Display a file specific popup menu"
  (interactive "e")
  (mouse-set-point event)
  (let* ((line-info (svn-status-get-line-information))
         (name (svn-status-line-info->filename line-info)))
    (when line-info
      (easy-menu-define svn-status-actual-popup-menu nil nil
        (append (list name) svn-status-file-popup-menu-list))
      (svn-status-face-set-temporary-during-popup
       'svn-status-marked-popup-face (svn-point-at-bol) (svn-point-at-eol)
       svn-status-actual-popup-menu))))

(defun svn-status-face-set-temporary-during-popup (face begin end menu &optional prefix)
  "Put FACE on BEGIN and END in the buffer during Popup MENU.
PREFIX is passed to `popup-menu'."
  (let (o)
    (unwind-protect
        (progn
          (setq o (make-overlay begin end))
          (overlay-put o 'face face)
          (sit-for 0)
          (popup-menu menu prefix))
      (delete-overlay o))))

(defun svn-status-mode ()
  "Major mode used by psvn.el to display the output of \"svn status\".

The Output has the following format:
  FPH BASE CMTD Author   em File
F = Filemark
P = Property mark
H = History mark
BASE = local base revision
CMTD = last committed revision
Author = author of change
em = \"**\" or \"(Update Available)\" [see `svn-status-short-mod-flag-p']
     if file can be updated
File = path/filename

The following keys are defined:
\\{svn-status-mode-map}"
  (interactive)
  (kill-all-local-variables)

  (use-local-map svn-status-mode-map)
  (easy-menu-add svn-status-mode-menu)

  (setq major-mode 'svn-status-mode)
  (setq mode-name "svn-status")
  (setq mode-line-process 'svn-status-mode-line-process)
  (run-hooks 'svn-status-mode-hook)
  (let ((view-read-only nil))
    (toggle-read-only 1)))

(defun svn-status-update-mode-line ()
  (setq svn-status-mode-line-process
        (concat svn-status-mode-line-process-edit-flag svn-status-mode-line-process-status))
  (force-mode-line-update))

(defun svn-status-bury-buffer (arg)
  "Bury the buffers used by psvn.el
Currently this is:
  `svn-status-buffer-name'
  `svn-process-buffer-name'
  `svn-log-edit-buffer-name'
  *svn-property-edit*
  *svn-log*
  *svn-info*
When called with a prefix argument, ARG, switch back to the window configuration that was
in use before `svn-status' was called."
  (interactive "P")
  (cond (arg
         (when svn-status-initial-window-configuration
           (set-window-configuration svn-status-initial-window-configuration)))
        (t
         (let ((bl `(,svn-log-edit-buffer-name "*svn-property-edit*" "*svn-log*" "*svn-info*" ,svn-process-buffer-name)))
           (while bl
             (when (get-buffer (car bl))
               (bury-buffer (car bl)))
             (setq bl (cdr bl)))
           (when (string= (buffer-name) svn-status-buffer-name)
             (bury-buffer))))))

(defun svn-status-save-some-buffers (&optional tree)
  "Save all buffers visiting a file in TREE.
If TREE is not given, try `svn-status-base-dir' as TREE."
  (interactive)
  ;; (message "svn-status-save-some-buffers: tree1: %s" tree)
  (let ((ok t)
        (tree (or (svn-status-base-dir)
                  tree)))
    ;; (message "svn-status-save-some-buffers: tree2: %s" tree)
    (unless tree
      (error "Not in a svn project tree"))
    (dolist (buffer (buffer-list))
      (with-current-buffer buffer
        (when (buffer-modified-p)
          (let ((file (buffer-file-name)))
            (when file
              (let ((root (svn-status-base-dir (file-name-directory file))))
                ;; (message "svn-status-save-some-buffers: file: %s, root: %s" file root)
                (when (and root
                           (string= root tree)
                           ;; buffer is modified and in the tree TREE.
                           (or (y-or-n-p (concat "Save buffer " (buffer-name) "? "))
                               (setq ok nil)))
                  (save-buffer))))))))
    ok))

(defun svn-status-find-files ()
  "Open selected file(s) for editing.
See `svn-status-marked-files' for what counts as selected."
  (interactive)
  (let ((fnames (mapcar 'svn-status-line-info->full-path (svn-status-marked-files))))
    (mapc 'find-file fnames)))


(defun svn-status-find-file-other-window ()
  "Open the file in the other window for editing."
  (interactive)
  (svn-status-ensure-cursor-on-file)
  (find-file-other-window (svn-status-line-info->filename
                           (svn-status-get-line-information))))

(defun svn-status-find-file-other-window-noselect ()
  "Open the file in the other window for editing, but don't select it."
  (interactive)
  (svn-status-ensure-cursor-on-file)
  (display-buffer
   (find-file-noselect (svn-status-line-info->filename
                        (svn-status-get-line-information)))))

(defun svn-status-view-file-other-window ()
  "Open the file in the other window for viewing."
  (interactive)
  (svn-status-ensure-cursor-on-file)
  (view-file-other-window (svn-status-line-info->filename
                           (svn-status-get-line-information))))

(defun svn-status-find-file-or-examine-directory ()
  "If point is on a directory, run `svn-status' on that directory.
Otherwise run `find-file'."
  (interactive)
  (svn-status-ensure-cursor-on-file)
  (let ((line-info (svn-status-get-line-information)))
    (if (svn-status-line-info->directory-p line-info)
        (svn-status (svn-status-line-info->full-path line-info))
      (find-file (svn-status-line-info->filename line-info)))))

(defun svn-status-examine-parent ()
  "Run `svn-status' on the parent of the current directory."
  (interactive)
  (svn-status (expand-file-name "../")))

(defun svn-status-mouse-find-file-or-examine-directory (event)
  "Move point to where EVENT occurred, and do `svn-status-find-file-or-examine-directory'
EVENT could be \"mouse clicked\" or similar."
  (interactive "e")
  (mouse-set-point event)
  (svn-status-find-file-or-examine-directory))

(defun svn-status-line-info->ui-status (line-info)
  "Return the ui-status structure of LINE-INFO.
See `svn-status-make-ui-status' for information about the ui-status."
  (nth 0 line-info))

(defun svn-status-line-info->has-usermark (line-info) (nth 0 (nth 0 line-info)))
(defun svn-status-line-info->user-elide (line-info) (nth 1 (nth 0 line-info)))

(defun svn-status-line-info->filemark (line-info) (nth 1 line-info))
(defun svn-status-line-info->propmark (line-info) (nth 2 line-info))
(defun svn-status-line-info->filename (line-info) (nth 3 line-info))
(defun svn-status-line-info->filename-nondirectory (line-info)
  (file-name-nondirectory (svn-status-line-info->filename line-info)))
(defun svn-status-line-info->localrev (line-info)
  (if (>= (nth 4 line-info) 0)
      (nth 4 line-info)
    nil))
(defun svn-status-line-info->lastchangerev (line-info)
  "Return the last revision in which LINE-INFO was modified."
  (let ((l (nth 5 line-info)))
    (if (and l (>= l 0))
        l
      nil)))
(defun svn-status-line-info->author (line-info)
  "Return the last author that changed the item that is represented in LINE-INFO."
  (nth 6 line-info))
(defun svn-status-line-info->update-available (line-info)
  "Return whether LINE-INFO is out of date.
In other words, whether there is a newer version available in the
repository than the working copy."
  (nth 7 line-info))
(defun svn-status-line-info->locked (line-info)
  "Return whether LINE-INFO represents a locked file.
This is column three of the `svn status' output.
The result will be nil or \"L\".
\(A file becomes locked when an operation is interupted; run \\[svn-status-cleanup]'
to unlock it.\)"
  (nth 8 line-info))
(defun svn-status-line-info->historymark (line-info)
  "Mark from column four of output from `svn status'.
This will be nil unless the file is scheduled for addition with
history, when it will be \"+\"."
  (nth 9 line-info))
(defun svn-status-line-info->switched (line-info)
  "Return whether LINE-INFO is switched relative to its parent.
This is column five of the output from `svn status'.
The result will be nil or \"S\"."
  (nth 10 line-info))
(defun svn-status-line-info->repo-locked (line-info)
  "Return whether LINE-INFO contains some locking information.
This is column six of the output from `svn status'.
The result will be \"K\", \"O\", \"T\", \"B\" or nil."
  (nth 11 line-info))
(defun svn-status-line-info->psvn-extra-info (line-info)
  "Return a list of extra information for psvn associated with LINE-INFO.
This list holds currently only one element:
* The action after a commit or update."
  (nth 12 line-info))

(defun svn-status-line-info->is-visiblep (line-info)
  "Return whether the line is visible or not"
  (or (not (or (svn-status-line-info->hide-because-unknown line-info)
               (svn-status-line-info->hide-because-unmodified line-info)
               (svn-status-line-info->hide-because-custom-hide-function line-info)
               (svn-status-line-info->hide-because-user-elide line-info)))
      (svn-status-line-info->update-available line-info) ;; show the line, if an update is available
      (svn-status-line-info->psvn-extra-info line-info)  ;; show the line, if there is some extra info displayed on this line
      ))

(defun svn-status-line-info->hide-because-unknown (line-info)
  (and svn-status-hide-unknown
       (eq (svn-status-line-info->filemark line-info) ??)))

(defun svn-status-line-info->hide-because-custom-hide-function (line-info)
  (and svn-status-custom-hide-function
       (apply svn-status-custom-hide-function (list line-info))))

(defun svn-status-line-info->hide-because-unmodified (line-info)
  ;;(message " %S %S %S %S - %s" svn-status-hide-unmodified (svn-status-line-info->propmark line-info) ?_
  ;;         (svn-status-line-info->filemark line-info) (svn-status-line-info->filename line-info))
  (and svn-status-hide-unmodified
       (and (or (eq (svn-status-line-info->filemark line-info) ?_)
                (eq (svn-status-line-info->filemark line-info) ? ))
            (or (eq (svn-status-line-info->propmark line-info) ?_)
                (eq (svn-status-line-info->propmark line-info) ? )
                (eq (svn-status-line-info->propmark line-info) nil)))))

(defun svn-status-line-info->hide-because-user-elide (line-info)
  (eq (svn-status-line-info->user-elide line-info) t))

(defun svn-status-line-info->show-user-elide-continuation (line-info)
  (eq (svn-status-line-info->user-elide line-info) 'directory))

;; modify the line-info
(defun svn-status-line-info->set-filemark (line-info value)
  (setcar (nthcdr 1 line-info) value))

(defun svn-status-line-info->set-propmark (line-info value)
  (setcar (nthcdr 2 line-info) value))

(defun svn-status-line-info->set-localrev (line-info value)
  (setcar (nthcdr 4 line-info) value))

(defun svn-status-line-info->set-author (line-info value)
  (setcar (nthcdr 6 line-info) value))

(defun svn-status-line-info->set-lastchangerev (line-info value)
  (setcar (nthcdr 5 line-info) value))

(defun svn-status-line-info->set-repo-locked (line-info value)
  (setcar (nthcdr 11 line-info) value))

(defun svn-status-line-info->set-psvn-extra-info (line-info value)
  (setcar (nthcdr 12 line-info) value))

(defun svn-status-copy-current-line-info (arg)
  "Copy the current file name at point, using `svn-status-copy-filename-as-kill'.
If no file is at point, copy everything starting from ':' to the end of line."
  (interactive "P")
  (if (svn-status-get-line-information)
      (svn-status-copy-filename-as-kill arg)
    (save-excursion
      (goto-char (svn-point-at-bol))
      (when (looking-at ".+?: *\\(.+\\)$")
        (kill-new (svn-match-string-no-properties 1))
        (message "Copied: %s" (svn-match-string-no-properties 1))))))

(defun svn-status-copy-filename-as-kill (arg)
  "Copy the actual file name to the kill-ring.
When called with the prefix argument 0, use the full path name."
  (interactive "P")
  (let ((str (if (eq arg 0)
                 (svn-status-line-info->full-path (svn-status-get-line-information))
               (svn-status-line-info->filename (svn-status-get-line-information)))))
    (kill-new str)
    (message "Copied %s" str)))

(defun svn-status-get-child-directories (&optional dir)
  "Return a list of subdirectories for DIR"
  (interactive)
  (let ((this-dir (concat (expand-file-name (or dir (svn-status-line-info->filename (svn-status-get-line-information)))) "/"))
        (test-dir)
        (sub-dir-list))
    ;;(message "this-dir %S" this-dir)
    (dolist (line-info svn-status-info)
      (when (svn-status-line-info->directory-p line-info)
        (setq test-dir (svn-status-line-info->full-path line-info))
        (when (string= (file-name-directory test-dir) this-dir)
          (add-to-list 'sub-dir-list (file-relative-name (svn-status-line-info->full-path line-info)) t))))
    sub-dir-list))

(defun svn-status-toggle-elide (arg)
  "Toggle eliding of the current file or directory.
When called with a prefix argument, toggle the hiding of all subdirectories for the current directory."
  (interactive "P")
  (if arg
      (let ((cur-line (svn-status-line-info->filename (svn-status-get-line-information))))
        (when (svn-status-line-info->user-elide (svn-status-get-line-information))
          (svn-status-toggle-elide nil))
        (dolist (dir-name (svn-status-get-child-directories))
          (svn-status-goto-file-name dir-name)
          (svn-status-toggle-elide nil))
        (svn-status-goto-file-name cur-line))
    (let ((st-info svn-status-info)
          (fname)
          (test (svn-status-line-info->filename (svn-status-get-line-information)))
          (len-test)
          (len-fname)
          (new-elide-mark t)
          (elide-mark))
      (if (member test svn-status-elided-list)
          (setq svn-status-elided-list (delete test svn-status-elided-list))
        (add-to-list 'svn-status-elided-list test))
      (when (string= test ".")
        (setq test ""))
      (setq len-test (length test))
      (while st-info
        (setq fname (svn-status-line-info->filename (car st-info)))
        (setq len-fname (length fname))
        (when (and (>= len-fname len-test)
                   (string= (substring fname 0 len-test) test))
          (setq elide-mark new-elide-mark)
          (when (or (string= fname ".")
                    (and (= len-fname len-test) (svn-status-line-info->directory-p (car st-info))))
            (message "Elided directory %s and all its files." fname)
            (setq new-elide-mark (not (svn-status-line-info->user-elide (car st-info))))
            (setq elide-mark (if new-elide-mark 'directory nil)))
          ;;(message "elide-mark: %S member: %S" elide-mark (member fname svn-status-elided-list))
          (when (and (member fname svn-status-elided-list) (not elide-mark))
            (setq svn-status-elided-list (delete fname svn-status-elided-list)))
          (setcar (nthcdr 1 (svn-status-line-info->ui-status (car st-info))) elide-mark))
        (setq st-info (cdr st-info))))
    ;;(message "svn-status-elided-list: %S" svn-status-elided-list)
    (svn-status-update-buffer)))

(defun svn-status-apply-elide-list ()
  "Elide files/directories according to `svn-status-elided-list'."
  (interactive)
  (let ((st-info svn-status-info)
        (fname)
        (len-fname)
        (test)
        (len-test)
        (elided-list)
        (elide-mark))
    (while st-info
      (setq fname (svn-status-line-info->filename (car st-info)))
      (setq len-fname (length fname))
      (setq elided-list svn-status-elided-list)
      (setq elide-mark nil)
      (while elided-list
        (setq test (car elided-list))
        (when (string= test ".")
          (setq test ""))
        (setq len-test (length test))
        (when (and (>= len-fname len-test)
                   (string= (substring fname 0 len-test) test))
          (setq elide-mark t)
          (when (or (string= fname ".")
                    (and (= len-fname len-test) (svn-status-line-info->directory-p (car st-info))))
            (setq elide-mark 'directory)))
        (setq elided-list (cdr elided-list)))
      ;;(message "fname: %s elide-mark: %S" fname elide-mark)
      (setcar (nthcdr 1 (svn-status-line-info->ui-status (car st-info))) elide-mark)
      (setq st-info (cdr st-info))))
  (svn-status-update-buffer))

(defun svn-status-update-with-command-list (cmd-list)
  (save-excursion
    (set-buffer svn-status-buffer-name)
    (let ((st-info)
          (found)
          (action)
          (fname (svn-status-line-info->filename (svn-status-get-line-information)))
          (fname-pos (point))
          (column (current-column)))
      (setq cmd-list (sort cmd-list '(lambda (item1 item2) (string-lessp (car item1) (car item2)))))
      (while cmd-list
        (unless st-info (setq st-info svn-status-info))
        ;;(message "%S" (caar cmd-list))
        (setq found nil)
        (while (and (not found) st-info)
          (setq found (string= (caar cmd-list) (svn-status-line-info->filename (car st-info))))
          ;;(message "found: %S" found)
          (unless found (setq st-info (cdr st-info))))
        (unless found
          (svn-status-message 3 "psvn: continue to search for %s" (caar cmd-list))
          (setq st-info svn-status-info)
          (while (and (not found) st-info)
            (setq found (string= (caar cmd-list) (svn-status-line-info->filename (car st-info))))
            (unless found (setq st-info (cdr st-info)))))
        (if found
            ;;update the info line
            (progn
              (setq action (cadar cmd-list))
              ;;(message "found %s, action: %S" (caar cmd-list) action)
              (svn-status-annotate-status-buffer-entry action (car st-info)))
          (svn-status-message 3 "psvn: did not find %s" (caar cmd-list)))
        (setq cmd-list (cdr cmd-list)))
      (if fname
          (progn
            (goto-char fname-pos)
            (svn-status-goto-file-name fname)
            (goto-char (+ column (svn-point-at-bol))))
        (goto-char (+ (next-overlay-change (point-min)) svn-status-default-column))))))

(defun svn-status-annotate-status-buffer-entry (action line-info)
  (let ((tag-string))
    (svn-status-goto-file-name (svn-status-line-info->filename line-info))
    (when (and (member action '(committed added))
               svn-status-commit-rev-number)
      (svn-status-line-info->set-localrev line-info svn-status-commit-rev-number)
      (svn-status-line-info->set-lastchangerev line-info svn-status-commit-rev-number))
    (when svn-status-last-commit-author
      (svn-status-line-info->set-author line-info svn-status-last-commit-author))
    (svn-status-line-info->set-psvn-extra-info line-info (list action))
    (cond ((equal action 'committed)
           (setq tag-string " <committed>")
           (when (member (svn-status-line-info->repo-locked line-info) '(?K))
             (svn-status-line-info->set-repo-locked line-info nil)))
          ((equal action 'added)
           (setq tag-string " <added>"))
          ((equal action 'deleted)
           (setq tag-string " <deleted>"))
          ((equal action 'replaced)
           (setq tag-string " <replaced>"))
          ((equal action 'updated)
           (setq tag-string " <updated>"))
          ((equal action 'updated-props)
           (setq tag-string " <updated-props>"))
          ((equal action 'conflicted)
           (setq tag-string " <conflicted>")
           (svn-status-line-info->set-filemark line-info ?C))
          ((equal action 'merged)
           (setq tag-string " <merged>"))
          ((equal action 'propset)
           ;;(setq tag-string " <propset>")
           (svn-status-line-info->set-propmark line-info svn-status-file-modified-after-save-flag))
          ((equal action 'added-wc)
           (svn-status-line-info->set-filemark line-info ?A)
           (svn-status-line-info->set-localrev line-info 0))
          ((equal action 'deleted-wc)
           (svn-status-line-info->set-filemark line-info ?D))
          (t
           (error "Unknown action '%s for %s" action (svn-status-line-info->filename line-info))))
    (when (and tag-string (not (member action '(conflicted merged))))
      (svn-status-line-info->set-filemark line-info ? )
      (svn-status-line-info->set-propmark line-info ? ))
    (let ((buffer-read-only nil))
      (delete-region (svn-point-at-bol) (svn-point-at-eol))
      (svn-insert-line-in-status-buffer line-info)
      (backward-char 1)
      (when tag-string
        (insert tag-string))
      (delete-char 1))))



;; (svn-status-update-with-command-list '(("++ideas" committed) ("a.txt" committed) ("alf")))
;; (svn-status-update-with-command-list (svn-status-parse-commit-output))

(defun svn-status-parse-commit-output ()
  "Parse the output of svn commit.
Return a list that is suitable for `svn-status-update-with-command-list'"
  (save-excursion
    (set-buffer svn-process-buffer-name)
    (let ((action)
          (file-name)
          (skip)
          (result))
      (goto-char (point-min))
      (setq svn-status-commit-rev-number nil)
      (setq skip nil) ; set to t whenever we find a line not about a committed file
      (while (< (point) (point-max))
        (cond ((= (svn-point-at-eol) (svn-point-at-bol)) ;skip blank lines
               (setq skip t))
              ((looking-at "Sending")
               (setq action 'committed))
              ((looking-at "Adding")
               (setq action 'added))
              ((looking-at "Deleting")
               (setq action 'deleted))
              ((looking-at "Replacing")
               (setq action 'replaced))
              ((looking-at "Transmitting file data")
               (setq skip t))
              ((looking-at "Committed revision \\([0-9]+\\)")
               (setq svn-status-commit-rev-number
                     (string-to-number (svn-match-string-no-properties 1)))
               (setq skip t))
              (t ;; this should never be needed(?)
               (setq action 'unknown)))
        (unless skip                                ;found an interesting line
          (forward-char 15)
          (when svn-status-operated-on-dot
            ;; when the commit used . as argument, delete the trailing directory
            ;; from the svn output
            (search-forward "/" nil t))
          (setq file-name (buffer-substring-no-properties (point) (svn-point-at-eol)))
          (unless svn-status-last-commit-author
            (setq svn-status-last-commit-author (car (svn-status-info-for-path (expand-file-name (concat default-directory file-name))))))
          (setq result (cons (list file-name action)
                             result))
          (setq skip nil))
        (forward-line 1))
      result)))
;;(svn-status-parse-commit-output)
;;(svn-status-annotate-status-buffer-entry)

(defun svn-status-parse-ar-output ()
  "Parse the output of svn add|remove.
Return a list that is suitable for `svn-status-update-with-command-list'"
  (save-excursion
    (set-buffer svn-process-buffer-name)
    (let ((action)
          (name)
          (skip)
          (result))
      (goto-char (point-min))
      (while (< (point) (point-max))
        (cond ((= (svn-point-at-eol) (svn-point-at-bol)) ;skip blank lines
               (setq skip t))
              ((looking-at "A")
               (setq action 'added-wc))
              ((looking-at "D")
               (setq action 'deleted-wc))
              (t ;; this should never be needed(?)
               (setq action 'unknown)))
        (unless skip ;found an interesting line
          (forward-char 10)
          (setq name (buffer-substring-no-properties (point) (svn-point-at-eol)))
          (setq result (cons (list name action)
                             result))
          (setq skip nil))
        (forward-line 1))
      result)))
;; (svn-status-parse-ar-output)
;; (svn-status-update-with-command-list (svn-status-parse-ar-output))

(defun svn-status-parse-update-output ()
  "Parse the output of svn update.
Return a list that is suitable for `svn-status-update-with-command-list'"
  (save-excursion
    (set-buffer svn-process-buffer-name)
    (setq svn-status-update-rev-number nil)
    (let ((action)
          (name)
          (skip)
          (result))
      (goto-char (point-min))
      (while (< (point) (point-max))
        (cond ((= (svn-point-at-eol) (svn-point-at-bol)) ;skip blank lines
               (setq skip t))
              ((looking-at "Updated to revision \\([0-9]+\\)")
               (setq svn-status-update-rev-number
                     (list t (string-to-number (svn-match-string-no-properties 1))))
               (setq skip t))
              ((looking-at "At revision \\([0-9]+\\)")
               (setq svn-status-update-rev-number
                     (list nil (string-to-number (svn-match-string-no-properties 1))))
               (setq skip t))
              ((looking-at "U")
               (setq action 'updated))
              ((looking-at "A")
               (setq action 'added))
              ((looking-at "D")
               (setq skip t))
               ;;(setq action 'deleted)) ;;deleted files are not displayed in the svn status output.
              ((looking-at "C")
               (setq action 'conflicted))
              ((looking-at "G")
               (setq action 'merged))

              ((looking-at " U")
               (setq action 'updated-props))

              (t ;; this should never be needed(?)
               (setq action (concat "parse-update: '"
                                    (buffer-substring-no-properties (point) (+ 2 (point))) "'"))))
        (unless skip ;found an interesting line
          (forward-char 3)
          (setq name (buffer-substring-no-properties (point) (svn-point-at-eol)))
          (setq result (cons (list name action)
                             result))
          (setq skip nil))
        (forward-line 1))
      result)))
;; (svn-status-parse-update-output)
;; (svn-status-update-with-command-list (svn-status-parse-update-output))

(defun svn-status-parse-property-output ()
  "Parse the output of svn propset.
Return a list that is suitable for `svn-status-update-with-command-list'"
  (save-excursion
    (set-buffer svn-process-buffer-name)
    (let ((result))
      (dolist (line (split-string (buffer-substring-no-properties (point-min) (point-max)) "\n"))
        (message "%s" line)
        (when (string-match "property '\\(.+\\)' set on '\\(.+\\)'" line)
          ;;(message "property %s - file %s" (match-string 1 line) (match-string 2 line))
          (setq result (cons (list (match-string 2 line) 'propset) result))))
      result)))

;; (svn-status-parse-property-output)
;; (svn-status-update-with-command-list (svn-status-parse-property-output))


(defun svn-status-line-info->symlink-p (line-info)
  "Return non-nil if LINE-INFO refers to a symlink, nil otherwise.
The value is the name of the file to which it is linked. \(See
`file-symlink-p'.\)

On win32 systems this won't work, even though symlinks are supported
by subversion on such systems."
  ;; on win32 would need to see how svn does symlinks
  (file-symlink-p (svn-status-line-info->filename line-info)))

(defun svn-status-line-info->directory-p (line-info)
  "Return t if LINE-INFO refers to a directory, nil otherwise.
Symbolic links to directories count as directories (see `file-directory-p')."
  (file-directory-p (svn-status-line-info->filename line-info)))

(defun svn-status-line-info->full-path (line-info)
  "Return the full path of the file represented by LINE-INFO."
  (expand-file-name
   (svn-status-line-info->filename line-info)))

;;Not convinced that this is the fastest way, but...
(defun svn-status-count-/ (string)
  "Return number of \"/\"'s in STRING."
  (let ((n 0)
        (last 0))
    (while (setq last (string-match "/" string (1+ last)))
      (setq n (1+ n)))
    n))

(defun svn-insert-line-in-status-buffer (line-info)
  "Format LINE-INFO and insert the result in the current buffer."
  (let ((usermark (if (svn-status-line-info->has-usermark line-info) "*" " "))
        (update-available (if (svn-status-line-info->update-available line-info)
                              (svn-add-face (if svn-status-short-mod-flag-p
                                                "** "
                                              " (Update Available)")
                                            'svn-status-update-available-face)
                            (if svn-status-short-mod-flag-p "   " "")))
        (filename  ;; <indentation>file or /path/to/file
                     (concat
                      (if (or svn-status-display-full-path
                              svn-status-hide-unmodified)
                          (svn-add-face
                           (let ((dir-name (file-name-as-directory
                                            (svn-status-line-info->directory-containing-line-info
                                             line-info nil))))
                             (if (and (<= 2 (length dir-name))
                                      (= ?. (aref dir-name 0))
                                      (= ?/ (aref dir-name 1)))
                                 (substring dir-name 2)
                               dir-name))
                           'svn-status-directory-face)
                        ;; showing all files, so add indentation
                        (make-string (* 2 (svn-status-count-/
                                           (svn-status-line-info->filename line-info)))
                                     32))
                      ;;symlinks get a different face
                      (let ((target (svn-status-line-info->symlink-p line-info)))
                        (if target
                            ;; name -> trget
                            ;; name gets symlink-face, target gets file/directory face
                            (concat
                             (svn-add-face (svn-status-line-info->filename-nondirectory line-info)
                                           'svn-status-symlink-face)
                             " -> "
                             (svn-status-choose-face-to-add
                              ;; TODO: could use different faces for
                              ;; unversioned targets and broken symlinks?
                              (svn-status-line-info->directory-p line-info)
                              target
                              'svn-status-directory-face
                              'svn-status-filename-face))
                          ;; else target is not a link
                          (svn-status-choose-face-to-add
                           (svn-status-line-info->directory-p line-info)
                           (svn-status-line-info->filename-nondirectory line-info)
                           'svn-status-directory-face
                           'svn-status-filename-face)))
                      ))
        (elide-hint (if (svn-status-line-info->show-user-elide-continuation line-info) " ..." "")))
    (svn-puthash (svn-status-line-info->filename line-info)
                 (point)
                 svn-status-filename-to-buffer-position-cache)
    (insert (svn-status-maybe-add-face
             (svn-status-line-info->has-usermark line-info)
             (concat usermark
                     (format svn-status-line-format
                             (svn-status-line-info->filemark line-info)
                             (or (svn-status-line-info->propmark line-info) ? )
                             (or (svn-status-line-info->historymark line-info) ? )
                             (or (svn-status-line-info->localrev line-info) "")
                             (or (svn-status-line-info->lastchangerev line-info) "")
                             (svn-status-line-info->author line-info))
                     (when svn-status-short-mod-flag-p update-available)
                     filename
                     (unless svn-status-short-mod-flag-p update-available)
                     (svn-status-maybe-add-string (svn-status-line-info->locked line-info)
                                                  " [ LOCKED ]" 'svn-status-locked-face)
                     (svn-status-maybe-add-string (svn-status-line-info->repo-locked line-info)
                                                  (let ((flag (svn-status-line-info->repo-locked line-info)))
                                                    (cond ((eq flag ?K) " [ REPO-LOCK-HERE ]")
                                                          ((eq flag ?O) " [ REPO-LOCK-OTHER ]")
                                                          ((eq flag ?T) " [ REPO-LOCK-STOLEN ]")
                                                          ((eq flag ?B) " [ REPO-LOCK-BROKEN ]")
                                                          (t " [ REPO-LOCK-UNKNOWN ]")))
                                                  'svn-status-locked-face)
                     (svn-status-maybe-add-string (svn-status-line-info->switched line-info)
                                                  " (switched)" 'svn-status-switched-face)
                     elide-hint)
             'svn-status-marked-face)
            "\n")))

(defun svn-status-redraw-status-buffer ()
  "Redraw the `svn-status-buffer-name' buffer.
Additionally clear the psvn-extra-info field in all line-info lists."
  (interactive)
  (dolist (line-info svn-status-info)
    (svn-status-line-info->set-psvn-extra-info line-info nil))
  (svn-status-update-buffer))

(defun svn-status-update-buffer ()
  "Update the `svn-status-buffer-name' buffer, using `svn-status-info'.
  This function does not access the repository."
  (interactive)
  ;(message "buffer-name: %s" (buffer-name))
  (unless (string= (buffer-name) svn-status-buffer-name)
    (set-buffer svn-status-buffer-name))
  (svn-status-mode)
  (when svn-status-refresh-info
    (when (eq svn-status-refresh-info 'once)
      (setq svn-status-refresh-info nil))
    (svn-status-parse-info t))
  (let ((st-info svn-status-info)
        (buffer-read-only nil)
        (start-pos)
        (overlay)
        (unmodified-count 0)    ;how many unmodified files are hidden
        (unknown-count 0)       ;how many unknown files are hidden
        (custom-hide-count 0)   ;how many files are hidden via svn-status-custom-hide-function
        (marked-count 0)        ;how many files are elided
        (user-elide-count 0)
        (first-line t)
        (fname (svn-status-line-info->filename (svn-status-get-line-information)))
        (fname-pos (point))
        (window-line-pos (svn-status-window-line-position (get-buffer-window (current-buffer))))
        (header-line-string)
        (column (current-column)))
    (delete-region (point-min) (point-max))
    (insert "\n")
    ;; Insert all files and directories
    (while st-info
      (setq start-pos (point))
      (cond ((or (svn-status-line-info->has-usermark (car st-info)) first-line)
             ;; Show a marked file and the "." always
             (svn-insert-line-in-status-buffer (car st-info))
             (setq first-line nil))
            ((svn-status-line-info->update-available (car st-info))
             (svn-insert-line-in-status-buffer (car st-info)))
            ((and svn-status-custom-hide-function
                  (apply svn-status-custom-hide-function (list (car st-info))))
             (setq custom-hide-count (1+ custom-hide-count)))
            ((svn-status-line-info->hide-because-user-elide (car st-info))
             (setq user-elide-count (1+ user-elide-count)))
            ((svn-status-line-info->hide-because-unknown (car st-info))
             (setq unknown-count (1+ unknown-count)))
            ((svn-status-line-info->hide-because-unmodified (car st-info))
             (setq unmodified-count (1+ unmodified-count)))
            (t
             (svn-insert-line-in-status-buffer (car st-info))))
      (when (svn-status-line-info->has-usermark (car st-info))
        (setq marked-count (+ marked-count 1)))
      (setq overlay (make-overlay start-pos (point)))
      (overlay-put overlay 'svn-info (car st-info))
      (setq st-info (cdr st-info)))
    ;; Insert status information at the buffer beginning
    (goto-char (point-min))
    (insert (format "svn status for directory %s%s\n"
                    default-directory
                    (if svn-status-head-revision (format " (status against revision: %s)"
                                                         svn-status-head-revision)
                      "")))
    (when svn-status-module-name
      (insert (format "Project name: %s\n" svn-status-module-name)))
    (when svn-status-branch-list
      (insert (format "Branches: %s\n" svn-status-branch-list)))
    (when svn-status-base-info
      (insert (concat "Repository Root: " (svn-status-base-info->repository-root) "\n"))
      (insert (concat "Repository Url:  " (svn-status-base-info->url) "\n")))
    (when svn-status-hide-unknown
      (insert
       (format "%d Unknown file(s) are hidden - press `?' to toggle hiding\n"
               unknown-count)))
    (when svn-status-hide-unmodified
      (insert
       (format "%d Unmodified file(s) are hidden - press `_' to toggle hiding\n"
               unmodified-count)))
    (when (> custom-hide-count 0)
      (insert
       (format "%d file(s) are hidden via the svn-status-custom-hide-function\n"
               custom-hide-count)))
    (when (> user-elide-count 0)
      (insert (format "%d file(s) elided\n" user-elide-count)))
    (insert (format "%d file(s) marked\n" marked-count))
    (setq header-line-string (concat (format svn-status-line-format
                                             70 80 72 "BASE" "CMTD" "Author")
                                     (if svn-status-short-mod-flag-p "em " "")
                                     "File"))
    (cond ((eq svn-status-use-header-line t)
           (setq header-line-format (concat "    " header-line-string)))
          ((eq svn-status-use-header-line 'inline)
           (insert "\n " header-line-string "\n")))
    (setq svn-start-of-file-list-line-number (+ (count-lines (point-min) (point)) 1))
    (if fname
        (progn
          (goto-char fname-pos)
          (svn-status-goto-file-name fname)
          (goto-char (+ column (svn-point-at-bol)))
          (when window-line-pos
            (recenter window-line-pos)))
      (goto-char (+ (next-overlay-change (point-min)) svn-status-default-column)))))

(defun svn-status-parse-info (arg)
  "Parse the svn info output for the base directory.
Show the repository url after this call in the `svn-status-buffer-name' buffer.
When called with the prefix argument 0, reset the information to nil.
This hides the repository information again.

When ARG is t, don't update the svn status buffer. This is useful for
non-interactive use."
  (interactive "P")
  (if (eq arg 0)
      (setq svn-status-base-info nil)
    (let ((svn-process-buffer-name "*svn-info-output*"))
      (when (get-buffer svn-process-buffer-name)
        (kill-buffer svn-process-buffer-name))
      (svn-run nil t 'parse-info "info" ".")
      (svn-status-parse-info-result)))
  (unless (eq arg t)
    (svn-status-update-buffer)))

(defun svn-status-parse-info-result ()
  "Parse the result from the svn info command.
Put the found values in `svn-status-base-info'."
  (let ((url)
        (repository-root)
        (last-changed-author))
    (save-excursion
      (set-buffer svn-process-buffer-name)
      (goto-char (point-min))
      (let ((case-fold-search t))
        (search-forward "url: ")
        (setq url (buffer-substring-no-properties (point) (svn-point-at-eol)))
        (when (search-forward "repository root: " nil t)
          (setq repository-root (buffer-substring-no-properties (point) (svn-point-at-eol))))
        (when (search-forward "last changed author: " nil t)
          (setq last-changed-author (buffer-substring-no-properties (point) (svn-point-at-eol))))))
    (setq svn-status-base-info `((url ,url) (repository-root ,repository-root) (last-changed-author ,last-changed-author)))))

(defun svn-status-base-info->url ()
  "Extract the url part from `svn-status-base-info'."
  (if svn-status-base-info
      (cadr (assoc 'url svn-status-base-info))
    ""))

(defun svn-status-base-info->repository-root ()
  "Extract the repository-root part from `svn-status-base-info'."
  (if svn-status-base-info
      (cadr (assoc 'repository-root svn-status-base-info))
    ""))

(defun svn-status-checkout-prefix-path ()
  "When only a part of the svn repository is checked out, return the file path for this checkout."
  (interactive)
  (svn-status-parse-info t)
  (let ((root (svn-status-base-info->repository-root))
        (url (svn-status-base-info->url))
        (p)
        (base-dir (svn-status-base-dir))
        (wc-checkout-prefix))
    (setq p (substring url (length root)))
    (setq wc-checkout-prefix (file-relative-name default-directory base-dir))
    (when (string= wc-checkout-prefix "./")
      (setq wc-checkout-prefix ""))
    ;; (message "svn-status-checkout-prefix-path: wc-checkout-prefix: '%s' p: '%s' base-dir: %s" wc-checkout-prefix p base-dir)
    (setq p (substring p 0 (- (length p) (length wc-checkout-prefix))))
    (when (interactive-p)
      (message "svn-status-checkout-prefix-path: '%s'" p))
    p))

(defun svn-status-ls (path &optional synchron)
  "Run svn ls PATH."
  (interactive "sPath for svn ls: ")
  (svn-run (not synchron) t 'ls "ls" path)
  (when synchron
    (split-string (with-current-buffer svn-process-buffer-name
                    (buffer-substring-no-properties (point-min) (point-max))))))

(defun svn-status-ls-branches ()
  "Show, which branches exist for the actual working copy.
Note: this command assumes the proposed standard svn repository layout."
  (interactive)
  (svn-status-parse-info t)
  (svn-status-ls (concat (svn-status-base-info->repository-root) "/branches")))

(defun svn-status-ls-tags ()
  "Show, which tags exist for the actual working copy.
Note: this command assumes the proposed standard svn repository layout."
  (interactive)
  (svn-status-parse-info t)
  (svn-status-ls (concat (svn-status-base-info->repository-root) "/tags")))

(defun svn-status-toggle-edit-cmd-flag (&optional reset)
  "Allow the user to edit the parameters for the next svn command.
This command toggles between
* editing the next command parameters (EditCmd)
* editing all all command parameters (EditCmd#)
* don't edit the command parameters ()
The string in parentheses is shown in the status line to show the state."
  (interactive)
  (cond ((or reset (eq svn-status-edit-svn-command 'sticky))
         (setq svn-status-edit-svn-command nil))
        ((eq svn-status-edit-svn-command nil)
         (setq svn-status-edit-svn-command t))
        ((eq svn-status-edit-svn-command t)
         (setq svn-status-edit-svn-command 'sticky)))
  (cond ((eq svn-status-edit-svn-command t)
         (setq svn-status-mode-line-process-edit-flag " EditCmd"))
        ((eq svn-status-edit-svn-command 'sticky)
         (setq svn-status-mode-line-process-edit-flag " EditCmd#"))
        (t
         (setq svn-status-mode-line-process-edit-flag "")))
  (svn-status-update-mode-line))

(defun svn-status-goto-root-or-return ()
  "Bounce point between the root (\".\") and the current line."
  (interactive)
  (if (string= (svn-status-line-info->filename (svn-status-get-line-information)) ".")
      (when svn-status-root-return-info
        (svn-status-goto-file-name
         (svn-status-line-info->filename svn-status-root-return-info)))
    (setq svn-status-root-return-info (svn-status-get-line-information))
    (svn-status-goto-file-name ".")))

(defun svn-status-next-line (nr-of-lines)
  "Go to the next line that holds a file information.
When called with a prefix argument advance the given number of lines."
  (interactive "p")
  (while (progn
           (forward-line nr-of-lines)
           (and (not (eobp))
                (not (svn-status-get-line-information)))))
  (when (svn-status-get-line-information)
    (goto-char (+ (svn-point-at-bol) svn-status-default-column))))

(defun svn-status-previous-line (nr-of-lines)
  "Go to the previous line that holds a file information.
When called with a prefix argument go back the given number of lines."
  (interactive "p")
  (while (progn
           (forward-line (- nr-of-lines))
           (and (not (bobp))
                (not (svn-status-get-line-information)))))
  (when (svn-status-get-line-information)
    (goto-char (+ (svn-point-at-bol) svn-status-default-column))))

(defun svn-status-dired-jump ()
  "Jump to a dired buffer, containing the file at point."
  (interactive)
  (let* ((line-info (svn-status-get-line-information))
         (file-full-path (if line-info
                             (svn-status-line-info->full-path line-info)
                           default-directory)))
    (let ((default-directory
            (file-name-as-directory
             (expand-file-name (if line-info
                                   (svn-status-line-info->directory-containing-line-info line-info t)
                                 default-directory)))))
      (if (fboundp 'dired-jump-back) (dired-jump-back) (dired-jump))) ;; Xemacs uses dired-jump-back
    (dired-goto-file file-full-path)))

(defun svn-status-possibly-negate-meaning-of-arg (arg &optional command)
  "Negate arg, if this-command is a member of svn-status-possibly-negate-meaning-of-arg."
  (unless command
    (setq command this-command))
  (if (member command svn-status-negate-meaning-of-arg-commands)
      (not arg)
    arg))

(defun svn-status-update (&optional arg)
  "Run 'svn status -v'.
When called with a prefix argument run 'svn status -vu'."
  (interactive "P")
  (unless (interactive-p)
    (save-excursion
      (set-buffer svn-process-buffer-name)
      (setq svn-status-update-previous-process-output
            (buffer-substring (point-min) (point-max)))))
  (svn-status default-directory arg))

(defun svn-status-get-line-information ()
  "Find out about the file under point.
The result may be parsed with the various `svn-status-line-info->...' functions."
  (if (eq major-mode 'svn-status-mode)
      (let ((svn-info nil))
        (dolist (overlay (overlays-at (point)))
          (setq svn-info (or svn-info
                             (overlay-get overlay 'svn-info))))
        svn-info)
    ;; different mode, means called not from the *svn-status* buffer
    (if svn-status-get-line-information-for-file
        (svn-status-make-line-info (if (eq svn-status-get-line-information-for-file 'relative)
                                       (file-relative-name (buffer-file-name) (svn-status-base-dir))
                                     (buffer-file-name)))
      (svn-status-make-line-info "."))))


(defun svn-status-get-file-list (use-marked-files)
  "Get either the selected files or the file under point.
USE-MARKED-FILES decides which we do.
See `svn-status-marked-files' for what counts as selected."
  (if use-marked-files
      (svn-status-marked-files)
    (list (svn-status-get-line-information))))

(defun svn-status-get-file-list-names (use-marked-files)
  (mapcar 'svn-status-line-info->filename (svn-status-get-file-list use-marked-files)))

(defun svn-status-get-file-information ()
  "Find out about the file under point.
The result may be parsed with the various `svn-status-line-info->...' functions.
When called from a *svn-status* buffer, do the same as `svn-status-get-line-information'.
When called from a file buffer provide a structure that contains the filename."
  (cond ((eq major-mode 'svn-status-mode)
         (svn-status-get-line-information))
        (t
         ;; a fake strukture that contains the buffername for the current buffer
         (svn-status-make-line-info (buffer-file-name (current-buffer))))))

(defun svn-status-select-line ()
    "Return information about the file under point.
\(Only used for debugging\)"
  (interactive)
  (let ((info (svn-status-get-line-information)))
    (if info
        (message "%S hide-because-unknown: %S hide-because-unmodified: %S" info
                 (svn-status-line-info->hide-because-unknown info)
                 (svn-status-line-info->hide-because-unmodified info))
      (message "No file on this line"))))

(defun svn-status-ensure-cursor-on-file ()
    "Raise an error unless point is on a valid file."
  (unless (svn-status-get-line-information)
    (error "No file on the current line")))

(defun svn-status-directory-containing-point (allow-self)
  "Find the (full path of) directory containing the file under point.

If ALLOW-SELF and the file is a directory, return that directory,
otherwise return the directory containing the file under point."
  ;;the first `or' below is because s-s-g-l-i returns `nil' if
  ;;point was outside the file list, but we need
  ;;s-s-l-i->f to return a string to add to `default-directory'.
  (let ((line-info (or (svn-status-get-line-information)
                       (svn-status-make-line-info))))
    (file-name-as-directory
     (expand-file-name
      (svn-status-line-info->directory-containing-line-info line-info allow-self)))))

(defun svn-status-line-info->directory-containing-line-info (line-info allow-self)
  "Find the directory containing for LINE-INFO.

If ALLOW-SELF is t and LINE-INFO refers to a directory then return the
directory itself, in all other cases find the parent directory"
  (if (and allow-self (svn-status-line-info->directory-p line-info))
      (svn-status-line-info->filename line-info)
    ;;The next `or' is because (file-name-directory "file") returns nil
    (or (file-name-directory (svn-status-line-info->filename line-info))
        ".")))

(defun svn-status-set-user-mark (arg)
  "Set a user mark on the current file or directory.
If the cursor is on a file this file is marked and the cursor advances to the next line.
If the cursor is on a directory all files in this directory are marked.

If this function is called with a prefix argument, only the current line is
marked, even if it is a directory."
  (interactive "P")
  (setq arg (svn-status-possibly-negate-meaning-of-arg arg 'svn-status-set-user-mark))
  (let ((info (svn-status-get-line-information)))
    (if info
        (progn
          (svn-status-apply-usermark t arg)
          (svn-status-next-line 1))
      (message "No file on this line - cannot set a mark"))))

(defun svn-status-unset-user-mark (arg)
  "Remove a user mark on the current file or directory.
If the cursor is on a file, this file is unmarked and the cursor advances to the next line.
If the cursor is on a directory, all files in this directory are unmarked.

If this function is called with a prefix argument, only the current line is
unmarked, even if is a directory."
  (interactive "P")
  (setq arg (svn-status-possibly-negate-meaning-of-arg arg 'svn-status-set-user-mark))
  (let ((info (svn-status-get-line-information)))
    (if info
        (progn
          (svn-status-apply-usermark nil arg)
          (svn-status-next-line 1))
      (message "No file on this line - cannot unset a mark"))))

(defun svn-status-unset-user-mark-backwards ()
  "Remove a user mark from the previous file.
Then move to that line."
  ;; This is consistent with `dired-unmark-backward' and
  ;; `cvs-mode-unmark-up'.
  (interactive)
  (let ((info (save-excursion
                (svn-status-next-line -1)
                (svn-status-get-line-information))))
    (if info
        (progn
          (svn-status-next-line -1)
          (svn-status-apply-usermark nil t))
      (message "No file on previous line - cannot unset a mark"))))

(defun svn-status-apply-usermark (set-mark only-this-line)
  "Do the work for the various marking/unmarking functions."
  (let* ((st-info svn-status-info)
         (mark-count 0)
         (line-info (svn-status-get-line-information))
         (file-name (svn-status-line-info->filename line-info))
         (sub-file-regexp (if (file-directory-p file-name)
                              (concat "^" (regexp-quote
                                           (file-name-as-directory file-name)))
                            nil))
         (newcursorpos-fname)
         (i-fname)
         (first-line t)
         (current-line svn-start-of-file-list-line-number))
    (while st-info
      (when (or (svn-status-line-info->is-visiblep (car st-info)) first-line)
        (setq current-line (1+ current-line))
        (setq first-line nil))
      (setq i-fname (svn-status-line-info->filename (car st-info)))
      (when (or (string= file-name i-fname)
                (when sub-file-regexp
                  (string-match sub-file-regexp i-fname)))
        (when (svn-status-line-info->is-visiblep (car st-info))
          (when (or (not only-this-line) (string= file-name i-fname))
            (setq newcursorpos-fname i-fname)
            (unless (eq (car (svn-status-line-info->ui-status (car st-info))) set-mark)
              (setcar (svn-status-line-info->ui-status (car st-info)) set-mark)
              (setq mark-count (+ 1 mark-count))
              (save-excursion
                (let ((buffer-read-only nil))
                  (goto-line current-line)
                  (delete-region (svn-point-at-bol) (svn-point-at-eol))
                  (svn-insert-line-in-status-buffer (car st-info))
                  (delete-char 1)))
              (message "%s %s" (if set-mark "Marked" "Unmarked") i-fname)))))
      (setq st-info (cdr st-info)))
    ;;(svn-status-update-buffer)
    (svn-status-goto-file-name newcursorpos-fname)
    (when (> mark-count 1)
      (message "%s %d files" (if set-mark "Marked" "Unmarked") mark-count))))

(defun svn-status-apply-usermark-checked (check-function set-mark)
  "Mark or unmark files, whether a given function returns t.
The function is called with the line information. Therefore the
svn-status-line-info->* functions can be used in the check."
  (let ((st-info svn-status-info)
        (mark-count 0))
    (while st-info
      (when (apply check-function (list (car st-info)))
        (unless (eq (svn-status-line-info->has-usermark (car st-info)) set-mark)
          (setq mark-count (+ 1 mark-count))
          (message "%s %s"
                   (if set-mark "Marked" "Unmarked")
                   (svn-status-line-info->filename (car st-info))))
        (setcar (svn-status-line-info->ui-status (car st-info)) set-mark))
      (setq st-info (cdr st-info)))
    (svn-status-update-buffer)
    (when (> mark-count 1)
      (message "%s %d files" (if set-mark "Marked" "Unmarked") mark-count))))

(defun svn-status-mark-unknown (arg)
  "Mark all unknown files.
These are the files marked with '?' in the `svn-status-buffer-name' buffer.
If the function is called with a prefix arg, unmark all these files."
  (interactive "P")
  (svn-status-apply-usermark-checked
   '(lambda (info) (eq (svn-status-line-info->filemark info) ??)) (not arg)))

(defun svn-status-mark-added (arg)
  "Mark all added files.
These are the files marked with 'A' in the `svn-status-buffer-name' buffer.
If the function is called with a prefix ARG, unmark all these files."
  (interactive "P")
  (svn-status-apply-usermark-checked
   '(lambda (info) (eq (svn-status-line-info->filemark info) ?A)) (not arg)))

(defun svn-status-mark-modified (arg)
  "Mark all modified files.
These are the files marked with 'M' in the `svn-status-buffer-name' buffer.
Changed properties are considered.
If the function is called with a prefix ARG, unmark all these files."
  (interactive "P")
  (svn-status-apply-usermark-checked
   '(lambda (info) (or (eq (svn-status-line-info->filemark info) ?M)
                       (eq (svn-status-line-info->filemark info)
                           svn-status-file-modified-after-save-flag)
                       (eq (svn-status-line-info->propmark info) ?M)))
   (not arg)))

(defun svn-status-mark-modified-properties (arg)
  "Mark all files and directories with modified properties.
If the function is called with a prefix ARG, unmark all these entries."
  (interactive "P")
  (svn-status-apply-usermark-checked
   '(lambda (info) (or (eq (svn-status-line-info->propmark info) ?M)))
   (not arg)))

(defun svn-status-mark-deleted (arg)
  "Mark all files scheduled for deletion.
These are the files marked with 'D' in the `svn-status-buffer-name' buffer.
If the function is called with a prefix ARG, unmark all these files."
  (interactive "P")
  (svn-status-apply-usermark-checked
   '(lambda (info) (eq (svn-status-line-info->filemark info) ?D)) (not arg)))

(defun svn-status-mark-changed (arg)
  "Mark all files that could be committed.
This means we mark
* all modified files
* all files scheduled for addition
* all files scheduled for deletion

The last two categories include all copied and moved files.
If called with a prefix ARG, unmark all such files."
  (interactive "P")
  (svn-status-mark-added arg)
  (svn-status-mark-modified arg)
  (svn-status-mark-deleted arg))

(defun svn-status-unset-all-usermarks ()
  (interactive)
  (svn-status-apply-usermark-checked '(lambda (info) t) nil))

(defvar svn-status-regexp-history nil
  "History list of regular expressions used in svn status commands.")

(defun svn-status-read-regexp (prompt)
  (read-from-minibuffer prompt nil nil nil 'svn-status-regexp-history))

(defun svn-status-mark-filename-regexp (regexp &optional unmark)
  "Mark all files matching REGEXP.
If the function is called with a prefix arg, unmark all these files."
  (interactive
   (list (svn-status-read-regexp (concat (if current-prefix-arg "Unmark" "Mark")
                                         " files (regexp): "))
         (if current-prefix-arg t nil)))
  (svn-status-apply-usermark-checked
   '(lambda (info) (string-match regexp (svn-status-line-info->filename-nondirectory info))) (not unmark)))

(defun svn-status-mark-by-file-ext (ext &optional unmark)
  "Mark all files matching the given file extension EXT.
If the function is called with a prefix arg, unmark all these files."
  (interactive
   (list (read-string (concat (if current-prefix-arg "Unmark" "Mark")
                                         " files with extensions: "))
         (if current-prefix-arg t nil)))
  (svn-status-apply-usermark-checked
   '(lambda (info) (let ((case-fold-search nil))
                     (string-match (concat "\\." ext "$") (svn-status-line-info->filename-nondirectory info)))) (not unmark)))

(defun svn-status-toggle-hide-unknown ()
  (interactive)
  (setq svn-status-hide-unknown (not svn-status-hide-unknown))
  (svn-status-update-buffer))

(defun svn-status-toggle-hide-unmodified ()
  (interactive)
  (setq svn-status-hide-unmodified (not svn-status-hide-unmodified))
  (svn-status-update-buffer))

(defun svn-status-get-file-name-buffer-position (name)
  "Find the buffer position for a file.
If the file is not found, return nil."
  (let ((start-pos (let ((cached-pos (gethash name
                                              svn-status-filename-to-buffer-position-cache)))
                     (when cached-pos
                       (goto-char (previous-overlay-change cached-pos)))
                     (point)))
        (found))
    ;; performance optimization: search from point to end of buffer
    (while (and (not found) (< (point) (point-max)))
      (goto-char (next-overlay-change (point)))
      (when (string= name (svn-status-line-info->filename
                           (svn-status-get-line-information)))
        (setq start-pos (+ (point) svn-status-default-column))
        (setq found t)))
    ;; search from buffer start to point
    (goto-char (point-min))
    (while (and (not found) (< (point) start-pos))
      (goto-char (next-overlay-change (point)))
      (when (string= name (svn-status-line-info->filename
                           (svn-status-get-line-information)))
        (setq start-pos (+ (point) svn-status-default-column))
        (setq found t)))
    (and found start-pos)))

(defun svn-status-goto-file-name (name)
  "Move the cursor the the line that displays NAME."
  (let ((pos (svn-status-get-file-name-buffer-position name)))
    (if pos
        (goto-char pos)
      (svn-status-message 7 "Note: svn-status-goto-file-name: %s not found" name))))

(defun svn-status-find-info-for-file-name (name)
  (let* ((st-info svn-status-info)
         (info))
    (while st-info
      (when (string= name (svn-status-line-info->filename (car st-info)))
        (setq info (car st-info))
        (setq st-info nil)) ; terminate loop
      (setq st-info (cdr st-info)))
    info))

(defun svn-status-marked-files ()
  "Return all files marked by `svn-status-set-user-mark',
or (if no files were marked) the file under point."
  (if (eq major-mode 'svn-status-mode)
      (let* ((st-info svn-status-info)
             (file-list))
        (while st-info
          (when (svn-status-line-info->has-usermark (car st-info))
            (setq file-list (append file-list (list (car st-info)))))
          (setq st-info (cdr st-info)))
        (or file-list
            (if (svn-status-get-line-information)
                (list (svn-status-get-line-information))
              nil)))
    ;; different mode, means called not from the *svn-status* buffer
    (if svn-status-get-line-information-for-file
        (list (svn-status-make-line-info (if (eq svn-status-get-line-information-for-file 'relative)
                                             (file-relative-name (buffer-file-name) (svn-status-base-dir))
                                           (buffer-file-name))))
      (list (svn-status-make-line-info ".")))))

(defun svn-status-marked-file-names ()
  (mapcar 'svn-status-line-info->filename (svn-status-marked-files)))

(defun svn-status-some-files-marked-p ()
  "Return non-nil iff a file has been marked by `svn-status-set-user-mark'.
Unlike `svn-status-marked-files', this does not select the file under point
if no files have been marked."
  ;; `some' would be shorter but requires cl-seq at runtime.
  ;; (Because it accepts both lists and vectors, it is difficult to inline.)
  (loop for line-info in svn-status-info
        thereis (svn-status-line-info->has-usermark line-info)))

(defun svn-status-only-dirs-or-nothing-marked-p ()
  "Return non-nil iff only dirs has been marked by `svn-status-set-user-mark'."
  ;; `some' would be shorter but requires cl-seq at runtime.
  ;; (Because it accepts both lists and vectors, it is difficult to inline.)
  (loop for line-info in svn-status-info
        thereis (and (not (svn-status-line-info->directory-p line-info))
                     (svn-status-line-info->has-usermark line-info))))

(defun svn-status-ui-information-hash-table ()
  (let ((st-info svn-status-info)
        (svn-status-ui-information (make-hash-table :test 'equal)))
    (while st-info
      (svn-puthash (svn-status-line-info->filename (car st-info))
                   (svn-status-line-info->ui-status (car st-info))
                   svn-status-ui-information)
      (setq st-info (cdr st-info)))
    svn-status-ui-information))


(defun svn-status-create-arg-file (file-name prefix file-info-list postfix)
  (with-temp-file file-name
    (insert prefix)
    (let ((st-info file-info-list))
      (while st-info
        (insert (svn-status-line-info->filename (car st-info)))
        (insert "\n")
        (setq st-info (cdr st-info)))

    (insert postfix))))

(defun svn-status-show-process-buffer-internal (&optional scroll-to-top)
  (let ((cur-buff (current-buffer)))
    (unless svn-status-preserve-window-configuration
      (when (string= (buffer-name) svn-status-buffer-name)
        (delete-other-windows)))
    (pop-to-buffer svn-process-buffer-name)
    (svn-process-mode)
    (when scroll-to-top
      (goto-char (point-min)))
    (pop-to-buffer cur-buff)))

(defun svn-status-show-process-output (cmd &optional scroll-to-top)
  "Display the result of a svn command.
Consider svn-status-window-alist to choose the buffer name."
  (let ((window-mode (cadr (assoc cmd svn-status-window-alist)))
        (process-default-directory))
    (cond ((eq window-mode nil) ;; use *svn-process* buffer
           (setq svn-status-last-output-buffer-name svn-process-buffer-name))
          ((eq window-mode t) ;; use *svn-info* buffer
           (setq svn-status-last-output-buffer-name "*svn-info*"))
          ((eq window-mode 'invisible) ;; don't display the buffer
           (setq svn-status-last-output-buffer-name nil))
          (t
           (setq svn-status-last-output-buffer-name window-mode)))
    (when svn-status-last-output-buffer-name
      (if window-mode
          (progn
            (unless svn-status-preserve-window-configuration
              (when (string= (buffer-name) svn-status-buffer-name)
                (delete-other-windows)))
            (pop-to-buffer svn-process-buffer-name)
            (setq process-default-directory default-directory)
            (switch-to-buffer (get-buffer-create svn-status-last-output-buffer-name))
            (setq default-directory process-default-directory)
            (let ((buffer-read-only nil))
              (delete-region (point-min) (point-max))
              (insert-buffer-substring svn-process-buffer-name)
              (when scroll-to-top
                (goto-char (point-min))))
            (when (eq window-mode t) ;; *svn-info* buffer
              (svn-info-mode))
            (other-window 1))
        (svn-status-show-process-buffer-internal scroll-to-top)))))

(defun svn-status-svn-log-switches (arg)
  (cond ((eq arg 0)  '())
        ((or (eq arg -1) (eq arg '-)) '("-q"))
        (arg         '("-v"))
        (t           svn-status-default-log-arguments)))

(defun svn-status-show-svn-log (arg)
  "Run `svn log' on selected files.
The output is put into the *svn-log* buffer
The optional prefix argument ARG determines which switches are passed to `svn log':
 no prefix               --- use whatever is in the list `svn-status-default-log-arguments'
 prefix argument of -1:  --- use the -q switch (quiet)
 prefix argument of 0    --- use no arguments
 other prefix arguments: --- use the -v switch (verbose)

See `svn-status-marked-files' for what counts as selected."
  (interactive "P")
  (let ((switches (svn-status-svn-log-switches arg))
        (svn-status-get-line-information-for-file t))
    ;; (message "svn-status-show-svn-log %S" arg)
    (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-marked-files) "")
    (svn-run t t 'log "log" "--targets" svn-status-temp-arg-file switches)))

(defun svn-status-version ()
  "Show the version numbers for psvn.el and the svn command line client.
The version number of the client is cached in `svn-client-version'."
  (interactive)
  (let ((window-conf (current-window-configuration))
        (version-string))
    (if (or (interactive-p) (not svn-status-cached-version-string))
        (progn
          (svn-run nil t 'version "--version")
          (when (interactive-p)
            (svn-status-show-process-output 'info t))
          (with-current-buffer svn-status-last-output-buffer-name
            (goto-char (point-min))
            (setq svn-client-version
                  (when (re-search-forward "svn, version \\([0-9\.]+\\) " nil t)
                    (mapcar 'string-to-number (split-string (match-string 1) "\\."))))
            (let ((buffer-read-only nil))
              (goto-char (point-min))
              (insert (format "psvn.el revision: %s\n\n" svn-psvn-revision)))
            (setq version-string (buffer-substring-no-properties (point-min) (point-max))))
          (setq svn-status-cached-version-string version-string))
      (setq version-string svn-status-cached-version-string)
    (unless (interactive-p)
      (set-window-configuration window-conf)
      version-string))))

(defun svn-status-info ()
  "Run `svn info' on all selected files.
See `svn-status-marked-files' for what counts as selected."
  (interactive)
  (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-marked-files) "")
  (svn-run t t 'info "info" "--targets" svn-status-temp-arg-file))

(defun svn-status-info-for-path (path)
  "Run svn info on the given PATH.
Return some interesting parts of the resulting output.
At the moment a list containing the last changed author is returned."
  (let ((svn-process-buffer-name "*svn-info-output*")
        (last-changed-author))
    (svn-run nil t 'info "info" path)
    (with-current-buffer svn-process-buffer-name
      (goto-char (point-min))
      (when (search-forward "last changed author: " nil t)
        (setq last-changed-author (buffer-substring-no-properties (point) (svn-point-at-eol)))))
    (svn-status-message 7 "last-changed-author for '%s': %s" path last-changed-author)
    (list last-changed-author)))

(defun svn-status-blame (revision)
  "Run `svn blame' on the current file.
When called with a prefix argument, ask the user for the REVISION to use.
When called from a file buffer, go to the current line in the resulting blame output."
  (interactive "P")
  (when current-prefix-arg
    (setq revision (svn-status-read-revision-string "Blame for version: " "BASE")))
  (unless revision (setq revision "BASE"))
  (setq svn-status-blame-file-name (svn-status-line-info->filename (svn-status-get-file-information)))
  (svn-run t t 'blame "blame" svn-status-default-blame-arguments "-r" revision svn-status-blame-file-name))

(defun svn-status-show-svn-diff (arg)
  "Run `svn diff' on the current file.
If the current file is a directory, compare it recursively.
If there is a newer revision in the repository, the diff is done against HEAD,
otherwise compare the working copy with BASE.
If ARG then prompt for revision to diff against (unless arg is '-)
When called with a negative prefix argument, do a non recursive diff."
  (interactive "P")
  (let ((non-recursive (or (and (numberp arg) (< arg 0)) (eq arg '-)))
        (revision (if (and (not (eq arg '-)) arg) :ask :auto)))
    (svn-status-ensure-cursor-on-file)
    (svn-status-show-svn-diff-internal (list (svn-status-get-line-information)) (not non-recursive)
                                       revision)))

(defun svn-file-show-svn-diff (arg)
  "Run `svn diff' on the current file.
If there is a newer revision in the repository, the diff is done against HEAD,
otherwise compare the working copy with BASE.
If ARG then prompt for revision to diff against."
  (interactive "P")
  (svn-status-show-svn-diff-internal (list (svn-status-make-line-info buffer-file-name)) nil
                                     (if arg :ask :auto)))

(defun svn-status-show-svn-diff-for-marked-files (arg)
  "Run `svn diff' on all selected files.
If some files have been marked, compare those non-recursively;
this is because marking a directory with \\[svn-status-set-user-mark]
normally marks all of its files as well.
If no files have been marked, compare recursively the file at point.
If ARG then prompt for revision to diff against, else compare working copy with BASE."
  (interactive "P")
  (svn-status-show-svn-diff-internal (svn-status-marked-files)
                                     (not (svn-status-some-files-marked-p))
                                     (if arg :ask "BASE")))

(defun svn-status-diff-show-changeset (rev &optional user-confirmation)
  "Show the changeset for a given log entry.
When called with a prefix argument, ask the user for the revision."
  (let* ((upper-rev rev)
         (lower-rev (number-to-string (- (string-to-number upper-rev) 1)))
         (rev-arg (concat lower-rev ":" upper-rev)))
    (when user-confirmation
      (setq rev-arg (read-string "Revision for changeset: " rev-arg)))
    (svn-run nil t 'diff "diff" (concat "-r" rev-arg))
    (svn-status-activate-diff-mode)))

(defun svn-status-show-svn-diff-internal (line-infos recursive revision)
  ;; REVISION must be one of:
  ;; - a string: whatever the -r option allows.
  ;; - `:ask': asks the user to specify the revision, which then becomes
  ;;   saved in `minibuffer-history' rather than in `command-history'.
  ;; - `:auto': use "HEAD" if an update is known to exist, "BASE" otherwise.
  ;; In the future, `nil' might mean omit the -r option entirely;
  ;; but that currently seems to imply "BASE", so we just use that.
  (when (eq revision :ask)
    (setq revision (svn-status-read-revision-string
                    "Diff with files for version: " "PREV")))

  (setq svn-status-last-diff-options (list line-infos recursive revision))

  (let ((clear-buf t)
        (beginning nil))
    (dolist (line-info line-infos)
      (svn-run nil clear-buf 'diff "diff" svn-status-default-diff-arguments
                   "-r" (if (eq revision :auto)
                            (if (svn-status-line-info->update-available line-info)
                                "HEAD" "BASE")
                          revision)
                   (unless recursive "--non-recursive")
                   (svn-status-line-info->filename line-info))
      (setq clear-buf nil)

      ;; "svn diff --non-recursive" skips only subdirectories, not files.
      ;; But a non-recursive diff via psvn should skip files too, because
      ;; the user would have marked them if he wanted them to be compared.
      ;; So we'll look for the "Index: foo" line that marks the first file
      ;; in the diff output, and delete it and everything that follows.
      ;; This is made more complicated by the fact that `svn-status-activate-diff-mode'
      ;; expects the output to be left in the *svn-process* buffer.
      (unless recursive
        ;; Check `directory-p' relative to the `default-directory' of the
        ;; "*svn-status*" buffer, not that of the svn-process-buffer-name buffer.
        (let ((directory-p (svn-status-line-info->directory-p line-info)))
          (with-current-buffer svn-process-buffer-name
            (when directory-p
              (goto-char (or beginning (point-min)))
              (when (re-search-forward "^Index: " nil t)
                (delete-region (match-beginning 0) (point-max))))
            (goto-char (setq beginning (point-max))))))))
  (svn-status-activate-diff-mode))

(defun svn-status-diff-save-current-defun-as-kill ()
  "Copy the function name for the change at point to the kill-ring.
That function uses `add-log-current-defun'"
  (interactive)
  (let ((func-name (add-log-current-defun)))
    (if func-name
        (progn
          (kill-new func-name)
          (message "Copied %S" func-name))
      (message "No current defun detected."))))

(defun svn-status-diff-pop-to-commit-buffer ()
  "Temporary switch to the `svn-status-buffer-name' buffer and start a commit from there."
  (interactive)
  (let ((window-conf (current-window-configuration)))
    (svn-status-switch-to-status-buffer)
    (svn-status-commit)
    (set-window-configuration window-conf)
    (setq svn-status-pre-commit-window-configuration window-conf)
    (pop-to-buffer svn-log-edit-buffer-name)))

(defun svn-status-activate-diff-mode ()
  "Show the `svn-process-buffer-name' buffer, using the diff-mode."
  (svn-status-show-process-output 'diff t)
  (let ((working-directory default-directory))
    (save-excursion
      (set-buffer svn-status-last-output-buffer-name)
      (setq default-directory working-directory)
      (svn-status-diff-mode)
      (setq buffer-read-only t))))

(define-derived-mode svn-status-diff-mode fundamental-mode "svn-diff"
  "Major mode to display svn diffs. Derives from `diff-mode'.

Commands:
\\{svn-status-diff-mode-map}
"
  (let ((diff-mode-shared-map (copy-keymap svn-status-diff-mode-map))
        major-mode mode-name)
    (diff-mode)
    (set (make-local-variable 'revert-buffer-function) 'svn-status-diff-update)))

(defun svn-status-diff-update (arg noconfirm)
  "Rerun the last svn diff command and update the *svn-diff* buffer."
  (interactive)
  (svn-status-save-some-buffers)
  (save-window-excursion
    (apply 'svn-status-show-svn-diff-internal svn-status-last-diff-options)))

(defun svn-status-show-process-buffer ()
  "Show the content of the `svn-process-buffer-name' buffer"
  (interactive)
  (svn-status-show-process-output nil))

(defun svn-status-pop-to-partner-buffer ()
  "Pop to the `svn-status-partner-buffer' if that variable is set."
  (interactive)
  (when svn-status-partner-buffer
    (let ((cur-buf (current-buffer)))
      (pop-to-buffer svn-status-partner-buffer)
      (setq svn-status-partner-buffer cur-buf))))

(defun svn-status-pop-to-new-partner-buffer (buffer)
  "Call `pop-to-buffer' and register the current buffer as partner buffer for BUFFER."
  (let ((cur-buf (current-buffer)))
    (pop-to-buffer buffer)
    (setq svn-status-partner-buffer cur-buf)))

(defun svn-status-add-file-recursively (arg)
  "Run `svn add' on all selected files.
When a directory is added, add files recursively.
See `svn-status-marked-files' for what counts as selected.
When this function is called with a prefix argument, use the actual file instead."
  (interactive "P")
  (message "adding: %S" (svn-status-get-file-list-names (not arg)))
  (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-get-file-list (not arg)) "")
  (svn-run t t 'add "add" "--targets" svn-status-temp-arg-file))

(defun svn-status-add-file (arg)
  "Run `svn add' on all selected files.
When a directory is added, don't add the files of the directory
 (svn add --non-recursive <file-list> is called).
See `svn-status-marked-files' for what counts as selected.
When this function is called with a prefix argument, use the actual file instead."
  (interactive "P")
  (message "adding: %S" (svn-status-get-file-list-names (not arg)))
  (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-get-file-list (not arg)) "")
  (svn-run t t 'add "add" "--non-recursive" "--targets" svn-status-temp-arg-file))

(defun svn-status-lock (arg)
  "Run `svn lock' on all selected files.
See `svn-status-marked-files' for what counts as selected."
  (interactive "P")
  (message "locking: %S" (svn-status-get-file-list-names t))
  (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-get-file-list t) "")
  (svn-run t t 'lock "lock" "--targets" svn-status-temp-arg-file))

(defun svn-status-unlock (arg)
  "Run `svn unlock' on all selected files.
See `svn-status-marked-files' for what counts as selected."
  (interactive "P")
  (message "unlocking: %S" (svn-status-get-file-list-names t))
  (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-get-file-list t) "")
  (svn-run t t 'unlock "unlock" "--targets" svn-status-temp-arg-file))

(defun svn-status-make-directory (dir)
  "Run `svn mkdir DIR'."
  ;; TODO: Allow entering a URI interactively.
  ;; Currently, `read-file-name' corrupts it.
  (interactive (list (read-file-name "Make directory: "
                                     (svn-status-directory-containing-point t))))
  (unless (string-match "^[^:/]+://" dir) ; Is it a URI?
    (setq dir (file-relative-name dir)))
  (svn-run t t 'mkdir "mkdir" "--" dir))

(defun svn-status-mv ()
  "Prompt for a destination, and `svn mv' selected files there.
See `svn-status-marked-files' for what counts as `selected'.

If one file was selected then the destination DEST should be a
filename to rename the selected file to, or a directory to move the
file into; if multiple files were selected then DEST should be a
directory to move the selected files into.

The default DEST is the directory containing point.

BUG: If we've marked some directory containging a file as well as the
file itself, then we should just mv the directory, but this implementation
doesn't check for that.
SOLUTION: for each dir, umark all its contents (but not the dir
itself) before running mv."
  (interactive)
    (svn-status-mv-cp "mv" "Rename" "Move" "mv"))

(defun svn-status-cp ()
  "See `svn-status-mv'"
  (interactive)
  (svn-status-mv-cp "cp" "Copy" "Copy" "cp"))

(defun svn-status-mv-cp (command singleprompt manyprompt fallback)
  "Run svn COMMAND on marked files, prompting for destination

This function acts on `svn-status-marked-files': at the prompt the
user can enter a new file name, or an existing directory: this is used as the argument for svn COMMAND.
   COMMAND      --- string saying what to do: \"mv\" or \"cp\"
   SINGLEPROMPT --- string at start of prompt when one file marked
   MANYPROMPT   --- string at start of prompt when multiple files marked
   FALLBACK     --- If any marked file is unversioned, use this instead of 'svn COMMAND'"
  (let* ((marked-files (svn-status-marked-files))
         (num-of-files (length marked-files))
         dest)
    (if (= 1 num-of-files)
        ;; one file to act on: new name, or directory to hold results
        (setq dest (read-file-name
                    (format "%s %s to: " singleprompt
                            (svn-status-line-info->filename (car marked-files)))
                    (svn-status-directory-containing-point t)
                    (svn-status-line-info->full-path (car marked-files))))
      ;;TODO: (when file-exists-p but-no-dir-p dest (error "%s already exists" dest))
      ;;multiple files selected, so prompt for existing directory to mv them into.
      (setq dest (svn-read-directory-name
                  (format "%s %d files to directory: " manyprompt num-of-files)
                  (svn-status-directory-containing-point t) nil t))
      (unless (file-directory-p dest)
        (error "%s is not a directory" dest)))
    (when (string= dest "")
      (error "No destination entered"))
    (unless (string-match "^[^:/]+://" dest) ; Is it a URI?
      (setq dest (file-relative-name dest)))

    ;;do the move: svn mv only lets us move things once at a time, so
    ;;we need to run svn mv once for each file (hence second arg to
    ;;svn-run is nil.)

    ;;TODO: before doing any moving, For every marked directory,
    ;;ensure none of its contents are also marked, since we dont want
    ;;to move both file *and* its parent...
    ;; what about elided files? what if user marks a dir+contents, then presses `_' ?
;;   ;one solution:
;;      (dolist (original marked-files)
;;          (when (svn-status-line-info->directory-p original)
;;              ;; run  svn-status-goto-file-name to move point to line of file
;;              ;; run  svn-status-unset-user-mark to unmark dir+all contents
;;              ;; run  svn-status-set-user-mark   to remark dir
;;              ;; maybe check for local mods here, and unmark if user does't say --force?
;;              ))
    (dolist (original marked-files)
      (let ((original-name (svn-status-line-info->filename original))
            (original-filemarks (svn-status-line-info->filemark original))
            (original-propmarks (svn-status-line-info->propmark original))
            (moved nil))
        (cond
         ((or (eq original-filemarks ?M)  ;local mods: maybe do `svn mv --force'
              (eq original-propmarks ?M)) ;local prop mods: maybe do `svn mv --force'
          (if (yes-or-no-p
               (format "%s has local modifications; use `--force' to really move it? " original-name))
              (progn
                (svn-status-run-mv-cp command original-name dest t)
                (setq moved t))
            (message "Not acting on %s" original-name)))
         ((eq original-filemarks ??) ;original is unversioned: use fallback
          (if (yes-or-no-p (format "%s is unversioned.  Use `%s -i -- %s %s'? "
                                   original-name fallback original-name dest))
              ;; TODO: consider svn-call-process-function here also...
              (progn (call-process fallback nil (get-buffer-create svn-process-buffer-name) nil
                                   "-i" "--" original-name dest)
                     (setq moved t))
            ;;new files created by fallback are not in *svn-status* now,
            ;;TODO: so call (svn-status-update) here?
            (message "Not acting on %s" original-name)))

         ((eq original-filemarks ?A) ;;`A' (`svn add'ed, but not committed)
          (message "Not acting on %s (commit it first)" original-name))

         ((eq original-filemarks ? ) ;original is unmodified: can proceed
          (svn-status-run-mv-cp command original-name dest)
          (setq moved t))

         ;;file has some other mark (eg conflicted)
         (t
          (if (yes-or-no-p
               (format "The status of %s looks scary.  Risk moving it anyway? "
                       original-name))
              (progn
                (svn-status-run-mv-cp command original-name dest)
                (setq moved t))
            (message "Not acting on %s" original-name))))
        (when moved
          (message "psvn: did '%s' from %s to %s" command original-name dest)
          ;; Silently rename the visited file of any buffer visiting this file.
          (when (get-file-buffer original-name)
            (with-current-buffer (get-file-buffer original-name)
              (set-visited-file-name dest nil t))))))
    (svn-status-update)))

(defun svn-status-run-mv-cp (command original destination &optional force)
  "Actually run svn mv or svn cp.
This is just to prevent duplication in `svn-status-prompt-and-act-on-files'"
  (if force
      (svn-run nil t (intern command) command "--force" "--" original destination)
    (svn-run nil t (intern command) command "--" original destination))
;;;TODO: use something like the following instead of calling svn-status-update
;;;      at the end of svn-status-mv-cp.
;;   (let ((output (svn-status-parse-ar-output))
;;         newfile
;;         buffer-read-only) ; otherwise insert-line-in-status-buffer fails
;;     (dolist (new-file output)
;;       (when (eq (cadr new-file) 'added-wc)
;;         ;; files with 'wc-added action do not exist in *svn-status*
;;         ;; buffer yet, so give each of them their own line-info
;;         ;; TODO: need to insert the new line-info in a sensible place, ie in the correct directory! [svn-status-filename-to-buffer-position-cache might help?]

;;         (svn-insert-line-in-status-buffer
;;          (svn-status-make-line-info (car new-file)))))
;;     (svn-status-update-with-command-list output))
  )

(defun svn-status-revert ()
  "Run `svn revert' on all selected files.
See `svn-status-marked-files' for what counts as selected."
  (interactive)
  (let* ((marked-files (svn-status-marked-files))
         (num-of-files (length marked-files)))
    (when (yes-or-no-p
           (if (= 1 num-of-files)
               (format "Revert %s? " (svn-status-line-info->filename (car marked-files)))
             (format "Revert %d files? " num-of-files)))
      (message "reverting: %S" (svn-status-marked-file-names))
      (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-marked-files) "")
      (svn-run t t 'revert "revert" "--targets" svn-status-temp-arg-file))))

(defun svn-status-rm (force)
  "Run `svn rm' on all selected files.
See `svn-status-marked-files' for what counts as selected.
When called with a prefix argument add the command line switch --force.

Forcing the deletion can also be used to delete files not under svn control."
  (interactive "P")
  (let* ((marked-files (svn-status-marked-files))
         (num-of-files (length marked-files)))
    (when (yes-or-no-p
           (if (= 1 num-of-files)
               (format "%sRemove %s? " (if force "Force " "") (svn-status-line-info->filename (car marked-files)))
             (format "%sRemove %d files? " (if force "Force " "") num-of-files)))
      (message "removing: %S" (svn-status-marked-file-names))
      (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-marked-files) "")
      (if force
          (save-excursion
            (svn-run t t 'rm "rm" "--force" "--targets" svn-status-temp-arg-file)
            (dolist (to-delete (svn-status-marked-files))
              (when (eq (svn-status-line-info->filemark to-delete) ??)
                (svn-status-goto-file-name (svn-status-line-info->filename to-delete))
                (let ((buffer-read-only nil))
                  (delete-region (svn-point-at-bol) (+ 1 (svn-point-at-eol)))
                  (delete to-delete svn-status-info)))))
        (svn-run t t 'rm "rm" "--targets" svn-status-temp-arg-file)))))

(defun svn-status-update-cmd (arg)
  "Run svn update.
When called with a prefix argument, ask the user for the revision to update to.
When called with a negative prefix argument, only update the selected files."
  (interactive "P")
  (let* ((selective-update (or (and (numberp arg) (< arg 0)) (eq arg '-)))
         (rev (when arg (svn-status-read-revision-string
                         (if selective-update
                             (format "Selected entries: Run svn update -r ")
                           (format "Directory: %s: Run svn update -r " default-directory))
                         (if selective-update "HEAD" nil)))))
    (if selective-update
        (progn
          (message "Running svn-update for %s" (svn-status-marked-file-names))
          (svn-run t t 'update "update"
                   (when rev (list "-r" rev))
                   (list "--non-interactive")
                   (svn-status-marked-file-names)))
      (message "Running svn-update for %s" default-directory)
      (svn-run t t 'update "update"
               (when rev (list "-r" rev))
               (list "--non-interactive") (expand-file-name default-directory)))))

(defun svn-status-commit ()
  "Commit selected files.
If some files have been marked, commit those non-recursively;
this is because marking a directory with \\[svn-status-set-user-mark]
normally marks all of its files as well.
If no files have been marked, commit recursively the file at point."
  (interactive)
  (svn-status-save-some-buffers)
  (let* ((selected-files (svn-status-marked-files)))
    (setq svn-status-files-to-commit selected-files
          svn-status-recursive-commit (not (svn-status-only-dirs-or-nothing-marked-p)))
    (svn-log-edit-show-files-to-commit)
    (svn-status-pop-to-commit-buffer)
    (when svn-log-edit-insert-files-to-commit
      (svn-log-edit-insert-files-to-commit))
    (when svn-log-edit-show-diff-for-commit
      (svn-log-edit-svn-diff nil))))

(defun svn-status-pop-to-commit-buffer ()
  "Pop to the svn commit buffer.
If a saved log message exists in `svn-log-edit-file-name' insert it in the buffer."
  (interactive)
  (setq svn-status-pre-commit-window-configuration (current-window-configuration))
  (let* ((use-existing-buffer (get-buffer svn-log-edit-buffer-name))
         (commit-buffer (get-buffer-create svn-log-edit-buffer-name))
         (dir default-directory)
         (log-edit-file-name))
    (pop-to-buffer commit-buffer)
    (setq default-directory dir)
    (setq log-edit-file-name (svn-log-edit-file-name))
    (unless use-existing-buffer
      (when (and log-edit-file-name (file-readable-p log-edit-file-name))
        (insert-file-contents log-edit-file-name)))
    (svn-log-edit-mode)))

(defun svn-status-switch-to-status-buffer ()
  "Switch to the `svn-status-buffer-name' buffer."
  (interactive)
  (switch-to-buffer svn-status-buffer-name))

(defun svn-status-pop-to-status-buffer ()
  "Pop to the `svn-status-buffer-name' buffer."
  (interactive)
  (pop-to-buffer svn-status-buffer-name))

(defun svn-status-via-bookmark (bookmark)
  "Allows a quick selection of a bookmark in `svn-bookmark-list'.
Run `svn-status' on the selected bookmark."
  (interactive
   (list
    (let ((completion-ignore-case t))
      (funcall svn-status-completing-read-function "SVN status bookmark: " svn-bookmark-list))))
  (unless bookmark
    (error "No bookmark specified"))
  (let ((directory (cdr (assoc bookmark svn-bookmark-list))))
    (if (file-directory-p directory)
        (svn-status directory)
      (error "%s is not a directory" directory))))

(defun svn-status-export ()
  "Run `svn export' for the current working copy.
Ask the user for the destination path.
`svn-status-default-export-directory' is suggested as export directory."
  (interactive)
  (let* ((src default-directory)
         (dir1-name (nth 1 (nreverse (split-string src "/"))))
         (dest (read-file-name (format "Export %s to " src) (concat svn-status-default-export-directory dir1-name))))
    (svn-run t t 'export "export" (expand-file-name src) (expand-file-name dest))
    (message "svn-status-export %s %s" src dest)))

(defun svn-status-cleanup (arg)
  "Run `svn cleanup' on all selected files.
See `svn-status-marked-files' for what counts as selected.
When this function is called with a prefix argument, use the actual file instead."
  (interactive "P")
  (let ((file-names (svn-status-get-file-list-names (not arg))))
    (if file-names
        (progn
          (message "svn-status-cleanup %S" file-names)
          (svn-run t t 'cleanup (append (list "cleanup") file-names)))
      (message "No valid file selected - No status cleanup possible"))))

(defun svn-status-resolved ()
  "Run `svn resolved' on all selected files.
See `svn-status-marked-files' for what counts as selected."
  (interactive)
  (let* ((marked-files (svn-status-marked-files))
         (num-of-files (length marked-files)))
    (when (yes-or-no-p
           (if (= 1 num-of-files)
               (format "Resolve %s? " (svn-status-line-info->filename (car marked-files)))
             (format "Resolve %d files? " num-of-files)))
      (message "resolving: %S" (svn-status-marked-file-names))
      (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-marked-files) "")
      (svn-run t t 'resolved "resolved" "--targets" svn-status-temp-arg-file))))


(defun svn-status-svnversion ()
  "Run svnversion on the directory that contains the file at point."
  (interactive)
  (svn-status-ensure-cursor-on-file)
  (let ((simple-path (svn-status-line-info->filename (svn-status-get-line-information)))
        (full-path (svn-status-line-info->full-path (svn-status-get-line-information)))
        (version))
    (unless (file-directory-p simple-path)
      (setq simple-path (or (file-name-directory simple-path) "."))
      (setq full-path (file-name-directory full-path)))
    (setq version (shell-command-to-string (concat "svnversion -n " full-path)))
    (message "svnversion for '%s': %s" simple-path version)
    version))

;; --------------------------------------------------------------------------------
;; Update the `svn-status-buffer-name' buffer, when a file is saved
;; --------------------------------------------------------------------------------

(defvar svn-status-file-modified-after-save-flag ?m
  "Flag shown whenever a file is modified and saved in Emacs.
The flag is shown in the `svn-status-buffer-name' buffer.
Recommended values are ?m or ?M.")
(defun svn-status-after-save-hook ()
  "Set a modified indication, when a file is saved from a svn working copy."
  (let* ((svn-dir (car-safe svn-status-directory-history))
         (svn-dir (when svn-dir (expand-file-name svn-dir)))
         (file-dir (file-name-directory (buffer-file-name)))
         (svn-dir-len (length (or svn-dir "")))
         (file-dir-len (length file-dir))
         (file-name))
    (when (and (get-buffer svn-status-buffer-name)
               svn-dir
               (>= file-dir-len svn-dir-len)
               (string= (substring file-dir 0 svn-dir-len) svn-dir))
      (setq file-name (substring (buffer-file-name) svn-dir-len))
      ;;(message "In svn-status directory %S" file-name)
      (let ((st-info svn-status-info)
            (i-fname))
        (while st-info
          (setq i-fname (svn-status-line-info->filename (car st-info)))
          ;;(message "i-fname=%S" i-fname)
          (when (and (string= file-name i-fname)
                     (not (eq (svn-status-line-info->filemark (car st-info)) ??)))
            (svn-status-line-info->set-filemark (car st-info)
                                                svn-status-file-modified-after-save-flag)
            (save-window-excursion
              (set-buffer svn-status-buffer-name)
              (save-excursion
                (let ((buffer-read-only nil)
                      (pos (svn-status-get-file-name-buffer-position i-fname)))
                  (if pos
                      (progn
                        (goto-char pos)
                        (delete-region (svn-point-at-bol) (svn-point-at-eol))
                        (svn-insert-line-in-status-buffer (car st-info))
                        (delete-char 1))
                    (svn-status-message 3 "psvn: file %s not found, updating %s buffer content..."
                             i-fname svn-status-buffer-name)
                    (svn-status-update-buffer))))))
          (setq st-info (cdr st-info))))))
  nil)

(add-hook 'after-save-hook 'svn-status-after-save-hook)

;; --------------------------------------------------------------------------------
;; vc-svn integration
;; --------------------------------------------------------------------------------
(defvar svn-status-state-mark-modeline t) ; modeline mark display or not
(defvar svn-status-state-mark-tooltip nil) ; modeline tooltip display

(defun svn-status-state-mark-modeline-dot (color)
  (propertize "    "
              'help-echo 'svn-status-state-mark-tooltip
              'display
              `(image :type xpm
                      :data ,(format "/* XPM */
static char * data[] = {
\"18 13 3 1\",
\"  c None\",
\"+ c #000000\",
\". c %s\",
\"                  \",
\"       +++++      \",
\"      +.....+     \",
\"     +.......+    \",
\"    +.........+   \",
\"    +.........+   \",
\"    +.........+   \",
\"    +.........+   \",
\"    +.........+   \",
\"     +.......+    \",
\"      +.....+     \",
\"       +++++      \",
\"                  \"};"
                                     color)
                      :ascent center)))

(defun svn-status-install-state-mark-modeline (color)
  (push `(svn-status-state-mark-modeline
          ,(svn-status-state-mark-modeline-dot color))
        mode-line-format)
  (force-mode-line-update t))

(defun svn-status-uninstall-state-mark-modeline ()
  (setq mode-line-format
        (remove-if #'(lambda (mode) (eq (car-safe mode)
                                        'svn-status-state-mark-modeline))
                   mode-line-format))
  (force-mode-line-update t))

(defun svn-status-update-state-mark-tooltip (tooltip)
  (setq svn-status-state-mark-tooltip tooltip))

(defun svn-status-update-state-mark (color)
  (svn-status-uninstall-state-mark-modeline)
  (svn-status-install-state-mark-modeline color))

(defsubst svn-status-in-vc-mode? ()
  "Is vc-svn active?"
  (and vc-mode (string-match "^ SVN" (svn-substring-no-properties vc-mode))))

(when svn-status-fancy-file-state-in-modeline
  (defadvice vc-find-file-hook (after svn-status-vc-svn-find-file-hook activate)
    "vc-find-file-hook advice for synchronizing psvn with vc-svn interface"
    (when (svn-status-in-vc-mode?) (svn-status-update-modeline)))

  (defadvice vc-after-save (after svn-status-vc-svn-after-save activate)
    "vc-after-save advice for synchronizing psvn when saving buffer"
    (when (svn-status-in-vc-mode?) (svn-status-update-modeline)))

  (defadvice ediff-refresh-mode-lines
    (around svn-modeline-ediff-fixup activate compile)
    "Fixup svn file status in the modeline when using ediff"
    (ediff-with-current-buffer ediff-buffer-A
                               (svn-status-uninstall-state-mark-modeline))
    (ediff-with-current-buffer ediff-buffer-B
                               (svn-status-uninstall-state-mark-modeline))
    ad-do-it
    (ediff-with-current-buffer ediff-buffer-A
                               (svn-status-update-modeline))
    (ediff-with-current-buffer ediff-buffer-B
                               (svn-status-update-modeline))))

(defun svn-status-update-modeline ()
  "Update modeline state dot mark properly"
  (when (and buffer-file-name (svn-status-in-vc-mode?))
    (svn-status-update-state-mark
     (svn-status-interprete-state-mode-color
      (vc-svn-state buffer-file-name)))))

(defsubst svn-status-interprete-state-mode-color (stat)
  "Interpret vc-svn-state symbol to mode line color"
  (case stat
    ('edited "tomato"      )
    ('up-to-date "GreenYellow" )
    ;; what is missing here??
    ;; ('unknown  "gray"        )
    ;; ('added    "blue"        )
    ;; ('deleted  "red"         )
    ;; ('unmerged "purple"      )
    (t "red")))

;; --------------------------------------------------------------------------------
;; Getting older revisions
;; --------------------------------------------------------------------------------

(defun svn-status-get-specific-revision (arg)
  "Retrieve older revisions.
The older revisions are stored in backup files named F.~REVISION~.

When the function is called without a prefix argument: get all marked files.
With a prefix argument: get only the actual file."
  (interactive "P")
  (svn-status-get-specific-revision-internal
   (svn-status-get-file-list (not arg)) :ask t))

(defun svn-status-get-specific-revision-internal (line-infos revision handle-relative-svn-status-dir)
  "Retrieve older revisions of files.
LINE-INFOS is a list of line-info structures (see
`svn-status-get-line-information').
REVISION is one of:
- a string: whatever the -r option allows.
- `:ask': asks the user to specify the revision, which then becomes
  saved in `minibuffer-history' rather than in `command-history'.
- `:auto': Use \"HEAD\" if an update is known to exist, \"BASE\" otherwise.

After the call, `svn-status-get-revision-file-info' will be an alist
\((WORKING-FILE-NAME . RETRIEVED-REVISION-FILE-NAME) ...).  These file
names are relative to the directory where `svn-status' was run."
  ;; In `svn-status-show-svn-diff-internal', there is a comment
  ;; that REVISION `nil' might mean omitting the -r option entirely.
  ;; That doesn't seem like a good idea with svn cat.

  ;; (message "svn-status-get-specific-revision-internal: %S %S" line-infos revision)

  (when (eq revision :ask)
    (setq revision (svn-status-read-revision-string
                    "Get files for version: " "PREV")))

  (let ((count (length line-infos)))
    (if (= count 1)
        (let ((line-info (car line-infos)))
          (message "Getting revision %s of %s"
                   (if (eq revision :auto)
                       (if (svn-status-line-info->update-available line-info)
                           "HEAD" "BASE")
                     revision)
                   (svn-status-line-info->filename line-info)))
      ;; We could compute "Getting HEAD of 8 files and BASE of 11 files"
      ;; but that'd be more bloat than it's worth.
      (message "Getting revision %s of %d files"
               (if (eq revision :auto) "HEAD or BASE" revision)
               count)))

  (let ((svn-status-get-specific-revision-file-info '()))
    (dolist (line-info line-infos)
      (let* ((revision (if (eq revision :auto)
                           (if (svn-status-line-info->update-available line-info)
                               "HEAD" "BASE")
                         revision))    ;must be a string by this point
             (file-name (svn-status-line-info->filename line-info))
             ;; If REVISION is e.g. "HEAD", should we find out the actual
             ;; revision number and save "foo.~123~" rather than "foo.~HEAD~"?
             ;; OTOH, `auto-mode-alist' already ignores ".~HEAD~" suffixes,
             ;; and if users often want to know the revision numbers of such
             ;; files, they can use svn:keywords.
             (file-name-with-revision (concat (file-name-nondirectory file-name) ".~" revision "~"))
             (default-directory (concat (svn-status-base-dir)
                                        (if handle-relative-svn-status-dir
                                            (file-relative-name default-directory (svn-status-base-dir))
                                          "")
                                        (file-name-directory file-name))))
        ;; `add-to-list' would unnecessarily check for duplicates.
        (push (cons file-name (concat (file-name-directory file-name) file-name-with-revision))
              svn-status-get-specific-revision-file-info)
        (svn-status-message 3 "svn-status-get-specific-revision-internal: file: %s, default-directory: %s"
                            file-name default-directory)
        (svn-status-message 3 "svn-status-get-specific-revision-internal: file-name-with-revision: %s %S"
                            file-name-with-revision (file-exists-p file-name-with-revision))
        (save-excursion
          (if (or (not (file-exists-p file-name-with-revision)) ;; file does not exist
                  (not (string= (number-to-string (string-to-number revision)) revision))) ;; revision is not a number
              (progn
                (message "Getting revision %s of %s, target: %s" revision file-name
                         (expand-file-name(concat default-directory file-name-with-revision)))
                (let ((content
                       (with-temp-buffer
                         (if (string= revision "BASE")
                             (insert-file-contents (concat (svn-wc-adm-dir-name)
                                                           "/text-base/"
                                                           (file-name-nondirectory file-name)
                                                           ".svn-base"))
                           (progn
                             (svn-run nil t 'cat "cat" "-r" revision
                                      (concat default-directory (file-name-nondirectory file-name)))
                             ;;todo: error processing
                             ;;svn: Filesystem has no item
                             ;;svn: file not found: revision `15', path `/trunk/file.txt'
                             (insert-buffer-substring svn-process-buffer-name)))
                         (buffer-string))))
                  (find-file file-name-with-revision)
                  (setq buffer-read-only nil)
                  (erase-buffer) ;Widen, because we'll save the whole buffer.
                  (insert content)
                  (goto-char (point-min))
                  (let ((write-file-functions nil)
                        (require-final-newline nil))
                    (save-buffer))))
            (find-file file-name-with-revision)))))
    ;;(message "default-directory: %s revision-file-info: %S" default-directory svn-status-get-specific-revision-file-info)
    (nreverse svn-status-get-specific-revision-file-info)))

(defun svn-status-ediff-with-revision (arg)
  "Run ediff on the current file with a different revision.
If there is a newer revision in the repository, the diff is done against HEAD,
otherwise compare the working copy with BASE.
If ARG then prompt for revision to diff against."
  (interactive "P")
  (let* ((svn-status-get-specific-revision-file-info
          (svn-status-get-specific-revision-internal
           (list (svn-status-make-line-info
                  (file-relative-name
                   (svn-status-line-info->full-path (svn-status-get-line-information))
                   (svn-status-base-dir))
                  nil nil nil nil nil nil
                  (svn-status-line-info->update-available (svn-status-get-line-information))))
           (if arg :ask :auto)
           nil))
         (ediff-after-quit-destination-buffer (current-buffer))
         (default-directory (svn-status-base-dir))
         (my-buffer (find-file-noselect (caar svn-status-get-specific-revision-file-info)))
         (base-buff (find-file-noselect (cdar svn-status-get-specific-revision-file-info)))
         (svn-transient-buffers (list my-buffer base-buff))
         (startup-hook '(svn-ediff-startup-hook)))
    (ediff-buffers base-buff my-buffer startup-hook)))

(defun svn-ediff-startup-hook ()
  ;; (message "svn-ediff-startup-hook: ediff-after-quit-hook-internal: %S" ediff-after-quit-hook-internal)
  (add-hook 'ediff-after-quit-hook-internal
            `(lambda ()
               (svn-ediff-exit-hook
                ',ediff-after-quit-destination-buffer ',svn-transient-buffers))
            nil 'local))

(defun svn-ediff-exit-hook (svn-buf tmp-bufs)
  ;; (message "svn-ediff-exit-hook: svn-buf: %s, tmp-bufs: %s" svn-buf tmp-bufs)
  ;; kill the temp buffers (and their associated windows)
  (dolist (tb tmp-bufs)
    (when (and tb (buffer-live-p tb) (not (buffer-modified-p tb)))
      (let* ((win (get-buffer-window tb t))
             (file-name (buffer-file-name tb))
             (is-temp-file (numberp (string-match "~\\([0-9]+\\|BASE\\)~" file-name))))
        ;; (message "svn-ediff-exit-hook - is-temp-file: %s, temp-buf:: %s - %s " is-temp-file (current-buffer) file-name)
        (when (and win (> (count-windows) 1)
                   (delete-window win)))
        (kill-buffer tb)
        (when (and is-temp-file svn-status-ediff-delete-temporary-files)
          (when (or (eq svn-status-ediff-delete-temporary-files t)
                    (y-or-n-p (format "Delete File '%s' ? " file-name)))
            (delete-file file-name))))))
  ;; switch back to the *svn* buffer
  (when (and svn-buf (buffer-live-p svn-buf)
             (not (get-buffer-window svn-buf t)))
    (ignore-errors (switch-to-buffer svn-buf))))


(defun svn-status-read-revision-string (prompt &optional default-value)
  "Prompt the user for a svn revision number."
  (interactive)
  (read-string prompt default-value))

(defun svn-file-show-svn-ediff (arg)
  "Run ediff on the current file with a previous revision.
If ARG then prompt for revision to diff against."
  (interactive "P")
  (let ((svn-status-get-line-information-for-file 'relative)
        (default-directory (svn-status-base-dir)))
    (svn-status-ediff-with-revision arg)))

;; --------------------------------------------------------------------------------
;; SVN process handling
;; --------------------------------------------------------------------------------

(defun svn-process-kill ()
  "Kill the current running svn process."
  (interactive)
  (let ((process (get-process "svn")))
    (if process
        (delete-process process)
      (message "No running svn process"))))

(defun svn-process-send-string (string &optional send-passwd)
  "Send a string to the running svn process.
This is useful, if the running svn process asks the user a question.
Note: use C-q C-j to send a line termination character."
  (interactive "sSend string to svn process: ")
  (save-excursion
    (set-buffer svn-process-buffer-name)
    (goto-char (point-max))
    (let ((buffer-read-only nil))
      (insert (if send-passwd (make-string (length string) ?.) string)))
    (set-marker (process-mark (get-process "svn")) (point)))
  (process-send-string "svn" string))

(defun svn-process-send-string-and-newline (string &optional send-passwd)
  "Send a string to the running svn process.
Just call `svn-process-send-string' with STRING and an end of line termination.
When called with a prefix argument, read the data from user as password."
  (interactive (let* ((use-passwd current-prefix-arg)
                      (s (if use-passwd
                             (read-passwd "Send secret line to svn process: ")
                           (read-string "Send line to svn process: "))))
                 (list s use-passwd)))
  (svn-process-send-string (concat string "\n") send-passwd))

;; --------------------------------------------------------------------------------
;; Search interface
;; --------------------------------------------------------------------------------

(defun svn-status-grep-files (regexp)
  "Run grep on selected file(s).
See `svn-status-marked-files' for what counts as selected."
  (interactive "sGrep files for: ")
  (unless grep-command
    (grep-compute-defaults))
  (let ((default-directory (svn-status-base-dir)))
    (grep (format "%s %s %s" grep-command (shell-quote-argument regexp)
                  (mapconcat 'identity (svn-status-marked-file-names) " ")))))

(defun svn-status-search-files (search-string)
  "Search selected file(s) for a fixed SEARCH-STRING.
See `svn-status-marked-files' for what counts as selected."
  (interactive "sSearch files for: ")
  (svn-status-grep-files (regexp-quote search-string)))

;; --------------------------------------------------------------------------------
;; Property List stuff
;; --------------------------------------------------------------------------------

(defun svn-status-property-list ()
  (interactive)
  (let ((file-names (svn-status-marked-file-names)))
    (if file-names
        (progn
          (svn-run t t 'proplist (append (list "proplist" "-v") file-names)))
      (message "No valid file selected - No property listing possible"))))

(defun svn-status-proplist-start ()
  (svn-status-ensure-cursor-on-file)
  (svn-run t t 'proplist-parse "proplist" (svn-status-line-info->filename
                                               (svn-status-get-line-information))))
(defun svn-status-property-edit-one-entry (arg)
  "Edit a property.
When called with a prefix argument, it is possible to enter a new property."
  (interactive "P")
  (setq svn-status-property-edit-must-match-flag (not arg))
  (svn-status-proplist-start))

(defun svn-status-property-set ()
  (interactive)
  (setq svn-status-property-edit-must-match-flag nil)
  (svn-status-proplist-start))

(defun svn-status-property-delete ()
  (interactive)
  (setq svn-status-property-edit-must-match-flag t)
  (svn-status-proplist-start))

(defun svn-status-property-parse-property-names ()
  ;(svn-status-show-process-buffer-internal t)
  (message "svn-status-property-parse-property-names")
  (let ((pl)
        (prop-name)
        (prop-value))
    (save-excursion
      (set-buffer svn-process-buffer-name)
      (goto-char (point-min))
      (forward-line 1)
      (while (looking-at "  \\(.+\\)")
        (setq pl (append pl (list (match-string 1))))
        (forward-line 1)))
    ;(cond last-command: svn-status-property-set, svn-status-property-edit-one-entry
    (cond ((eq last-command 'svn-status-property-edit-one-entry)
           ;;(message "svn-status-property-edit-one-entry")
           (setq prop-name
                 (completing-read "Set Property - Name: " (mapcar 'list pl)
                                  nil svn-status-property-edit-must-match-flag))
           (unless (string= prop-name "")
             (save-excursion
               (set-buffer svn-status-buffer-name)
               (svn-status-property-edit (list (svn-status-get-line-information))
                                         prop-name))))
          ((eq last-command 'svn-status-property-set)
           (message "svn-status-property-set")
           (setq prop-name
                 (completing-read "Set Property - Name: " (mapcar 'list pl) nil nil))
           (setq prop-value (read-from-minibuffer "Property value: "))
           (unless (string= prop-name "")
             (save-excursion
               (set-buffer svn-status-buffer-name)
               (message "Setting property %s := %s for %S" prop-name prop-value
                        (svn-status-marked-file-names))
               (let ((file-names (svn-status-marked-file-names)))
                 (when file-names
                   (svn-run nil t 'propset
                                (append (list "propset" prop-name prop-value) file-names))
                   )
                 )
               (message "propset finished.")
               )))
          ((eq last-command 'svn-status-property-delete)
           (setq prop-name
                 (completing-read "Delete Property - Name: " (mapcar 'list pl) nil t))
           (unless (string= prop-name "")
             (save-excursion
               (set-buffer svn-status-buffer-name)
               (let ((file-names (svn-status-marked-file-names)))
                 (when file-names
                   (message "Going to delete prop %s for %s" prop-name file-names)
                   (svn-run t t 'propdel
                                (append (list "propdel" prop-name) file-names))))))))))

(defun svn-status-property-edit (file-info-list prop-name &optional new-prop-value remove-values)
  (let* ((commit-buffer (get-buffer-create "*svn-property-edit*"))
         (dir default-directory)
         ;; now only one file is implemented ...
         (file-name (svn-status-line-info->filename (car file-info-list)))
         (prop-value))
    (message "Edit property %s for file %s" prop-name file-name)
    (svn-run nil t 'propget-parse "propget" prop-name file-name)
    (save-excursion
      (set-buffer svn-process-buffer-name)
      (setq prop-value (if (> (point-max) 1)
                           (buffer-substring (point-min) (- (point-max) 1))
                         "")))
    (setq svn-status-propedit-property-name prop-name)
    (setq svn-status-propedit-file-list file-info-list)
    (setq svn-status-pre-propedit-window-configuration (current-window-configuration))
    (pop-to-buffer commit-buffer)
    ;; If the buffer has been narrowed, `svn-prop-edit-done' will use
    ;; only the accessible part.  So we need not erase the rest here.
    (delete-region (point-min) (point-max))
    (setq default-directory dir)
    (insert prop-value)
    (svn-status-remove-control-M)
    (when new-prop-value
      (when (listp new-prop-value)
        (if remove-values
            (message "Remove prop values %S " new-prop-value)
          (message "Adding new prop values %S " new-prop-value))
        (while new-prop-value
          (goto-char (point-min))
          (if (re-search-forward (concat "^" (regexp-quote (car new-prop-value)) "$") nil t)
              (when remove-values
                (kill-whole-line 1))
            (unless remove-values
              (goto-char (point-max))
              (when (> (current-column) 0) (insert "\n"))
              (insert (car new-prop-value))))
          (setq new-prop-value (cdr new-prop-value)))))
    (svn-prop-edit-mode)))

(defun svn-status-property-set-property (file-info-list prop-name prop-value)
  "Set a property on a given file list."
  (save-excursion
    (set-buffer (get-buffer-create "*svn-property-edit*"))
    ;; If the buffer has been narrowed, `svn-prop-edit-do-it' will use
    ;; only the accessible part.  So we need not erase the rest here.
    (delete-region (point-min) (point-max))
    (insert prop-value))
  (setq svn-status-propedit-file-list (svn-status-marked-files))
  (setq svn-status-propedit-property-name prop-name)
  (svn-prop-edit-do-it nil)
  (svn-status-update))


(defun svn-status-get-directory (line-info)
  (let* ((file-name (svn-status-line-info->filename line-info))
         (file-dir (file-name-directory file-name)))
    ;;(message "file-dir: %S" file-dir)
    (if file-dir
        (substring file-dir 0 (- (length file-dir) 1))
      ".")))

(defun svn-status-get-file-list-per-directory (files)
  ;;(message "%S" files)
  (let ((dir-list nil)
        (i files)
        (j)
        (dir))
    (while i
      (setq dir (svn-status-get-directory (car i)))
      (setq j (assoc dir dir-list))
      (if j
          (progn
            ;;(message "dir already present %S %s" j dir)
            (setcdr j (append (cdr j) (list (car i)))))
        (setq dir-list (append dir-list (list (list dir (car i))))))
      (setq i (cdr i)))
    ;;(message "svn-status-get-file-list-per-directory: %S" dir-list)
    dir-list))

(defun svn-status-property-ignore-file ()
  (interactive)
  (let ((d-list (svn-status-get-file-list-per-directory (svn-status-marked-files)))
        (dir)
        (f-info)
        (ext-list))
    (while d-list
      (setq dir (caar d-list))
      (setq f-info (cdar d-list))
      (setq ext-list (mapcar '(lambda (i)
                                (svn-status-line-info->filename-nondirectory i)) f-info))
      ;;(message "ignore in dir %s: %S" dir f-info)
      (save-window-excursion
        (when (y-or-n-p (format "Ignore %S for %s? " ext-list dir))
          (svn-status-property-edit
           (list (svn-status-find-info-for-file-name dir)) "svn:ignore" ext-list)
          (svn-prop-edit-do-it nil)))   ; synchronous
      (setq d-list (cdr d-list)))
    (svn-status-update)))

(defun svn-status-property-ignore-file-extension ()
  (interactive)
  (let ((d-list (svn-status-get-file-list-per-directory (svn-status-marked-files)))
        (dir)
        (f-info)
        (ext-list))
    (while d-list
      (setq dir (caar d-list))
      (setq f-info (cdar d-list))
      ;;(message "ignore in dir %s: %S" dir f-info)
      (setq ext-list nil)
      (while f-info
        (add-to-list 'ext-list (concat "*."
                                       (file-name-extension
                                        (svn-status-line-info->filename (car f-info)))))
        (setq f-info (cdr f-info)))
      ;;(message "%S" ext-list)
      (save-window-excursion
        (when (y-or-n-p (format "Ignore %S for %s? " ext-list dir))
          (svn-status-property-edit
           (list (svn-status-find-info-for-file-name dir)) "svn:ignore"
           ext-list)
          (svn-prop-edit-do-it nil)))
      (setq d-list (cdr d-list)))
    (svn-status-update)))

(defun svn-status-property-edit-svn-ignore ()
  (interactive)
  (let* ((line-info (svn-status-get-line-information))
         (dir (if (svn-status-line-info->directory-p line-info)
                  (svn-status-line-info->filename line-info)
                (svn-status-get-directory line-info))))
    (svn-status-property-edit
     (list (svn-status-find-info-for-file-name dir)) "svn:ignore")
    (message "Edit svn:ignore on %s" dir)))


(defun svn-status-property-set-keyword-list ()
  "Edit the svn:keywords property on the marked files."
  (interactive)
  ;;(message "Set svn:keywords for %S" (svn-status-marked-file-names))
  (svn-status-property-edit (svn-status-marked-files) "svn:keywords"))

(defun svn-status-property-set-keyword-id (arg)
  "Set/Remove Id from the svn:keywords property.
Normally Id is added to the svn:keywords property.

When called with the prefix arg -, remove Id from the svn:keywords property."
  (interactive "P")
  (svn-status-property-edit (svn-status-marked-files) "svn:keywords" '("Id") (eq arg '-))
  (svn-prop-edit-do-it nil))

(defun svn-status-property-set-keyword-date (arg)
  "Set/Remove Date from the svn:keywords property.
Normally Date is added to the svn:keywords property.

When called with the prefix arg -, remove Date from the svn:keywords property."
  (interactive "P")
  (svn-status-property-edit (svn-status-marked-files) "svn:keywords" '("Date") (eq arg '-))
  (svn-prop-edit-do-it nil))


(defun svn-status-property-set-eol-style ()
  "Edit the svn:eol-style property on the marked files."
  (interactive)
  (svn-status-property-set-property
   (svn-status-marked-files) "svn:eol-style"
   (completing-read "Set svn:eol-style for the marked files: "
                    (mapcar 'list '("native" "CRLF" "LF" "CR"))
                    nil t)))

(defun svn-status-property-set-executable ()
  "Set the svn:executable property on the marked files."
  (interactive)
  (svn-status-property-set-property (svn-status-marked-files) "svn:executable" "*"))

(defun svn-status-property-set-mime-type ()
  "Set the svn:mime-type property on the marked files."
  (interactive)
  (require 'mailcap nil t)
  (let ((completion-ignore-case t)
        (mime-types (when (fboundp 'mailcap-mime-types)
                      (mailcap-mime-types))))
    (svn-status-property-set-property
     (svn-status-marked-files) "svn:mime-type"
     (funcall svn-status-completing-read-function "Set svn:mime-type for the marked files: "
              (mapcar (lambda (x) (cons x x)) ; for Emacs 21
                      (sort mime-types 'string<))))))

;; --------------------------------------------------------------------------------
;; svn-prop-edit-mode:
;; --------------------------------------------------------------------------------

(defvar svn-prop-edit-mode-map () "Keymap used in `svn-prop-edit-mode' buffers.")
(put 'svn-prop-edit-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-prop-edit-mode-map)
  (setq svn-prop-edit-mode-map (make-sparse-keymap))
  (define-key svn-prop-edit-mode-map [(control ?c) (control ?c)] 'svn-prop-edit-done)
  (define-key svn-prop-edit-mode-map [(control ?c) (control ?d)] 'svn-prop-edit-svn-diff)
  (define-key svn-prop-edit-mode-map [(control ?c) (control ?s)] 'svn-prop-edit-svn-status)
  (define-key svn-prop-edit-mode-map [(control ?c) (control ?l)] 'svn-prop-edit-svn-log)
  (define-key svn-prop-edit-mode-map [(control ?c) (control ?q)] 'svn-prop-edit-abort))

(easy-menu-define svn-prop-edit-mode-menu svn-prop-edit-mode-map
"'svn-prop-edit-mode' menu"
                  '("SVN-PropEdit"
                    ["Commit" svn-prop-edit-done t]
                    ["Show Diff" svn-prop-edit-svn-diff t]
                    ["Show Status" svn-prop-edit-svn-status t]
                    ["Show Log" svn-prop-edit-svn-log t]
                    ["Abort" svn-prop-edit-abort t]))

(defun svn-prop-edit-mode ()
  "Major Mode to edit file properties of files under svn control.
Commands:
\\{svn-prop-edit-mode-map}"
  (interactive)
  (kill-all-local-variables)
  (use-local-map svn-prop-edit-mode-map)
  (easy-menu-add svn-prop-edit-mode-menu)
  (setq major-mode 'svn-prop-edit-mode)
  (setq mode-name "svn-prop-edit"))

(defun svn-prop-edit-abort ()
  (interactive)
  (bury-buffer)
  (set-window-configuration svn-status-pre-propedit-window-configuration))

(defun svn-prop-edit-done ()
  (interactive)
  (svn-prop-edit-do-it t))

(defun svn-prop-edit-do-it (async)
  "Run svn propset `svn-status-propedit-property-name' with the content of the
*svn-property-edit* buffer."
  (message "svn propset %s on %s"
           svn-status-propedit-property-name
           (mapcar 'svn-status-line-info->filename svn-status-propedit-file-list))
  (save-excursion
    (set-buffer (get-buffer "*svn-property-edit*"))
    (when (fboundp 'set-buffer-file-coding-system)
      (set-buffer-file-coding-system svn-status-svn-file-coding-system nil))
    (setq svn-status-temp-file-to-remove
          (concat svn-status-temp-dir "svn-prop-edit.txt" svn-temp-suffix))
    (write-region (point-min) (point-max) svn-status-temp-file-to-remove nil 1))
  (when svn-status-propedit-file-list ; there are files to change properties
    (svn-status-create-arg-file svn-status-temp-arg-file ""
                                svn-status-propedit-file-list "")
    (setq svn-status-propedit-file-list nil)
    (svn-run async t 'propset "propset"
             svn-status-propedit-property-name
             "--targets" svn-status-temp-arg-file
             (when (eq svn-status-svn-file-coding-system 'utf-8)
               '("--encoding" "UTF-8"))
             "-F" (concat svn-status-temp-dir "svn-prop-edit.txt" svn-temp-suffix))
    (unless async (svn-status-remove-temp-file-maybe)))
  (when svn-status-pre-propedit-window-configuration
    (set-window-configuration svn-status-pre-propedit-window-configuration)))

(defun svn-prop-edit-svn-diff (arg)
  (interactive "P")
  (set-buffer svn-status-buffer-name)
  ;; Because propedit is not recursive in our use, neither is this diff.
  (svn-status-show-svn-diff-internal svn-status-propedit-file-list nil
                                     (if arg :ask "BASE")))

(defun svn-prop-edit-svn-log (arg)
  (interactive "P")
  (set-buffer svn-status-buffer-name)
  (svn-status-show-svn-log arg))

(defun svn-prop-edit-svn-status ()
  (interactive)
  (pop-to-buffer svn-status-buffer-name)
  (other-window 1))

;; --------------------------------------------------------------------------------
;; svn-log-edit-mode:
;; --------------------------------------------------------------------------------

(defvar svn-log-edit-mode-map () "Keymap used in `svn-log-edit-mode' buffers.")
(put 'svn-log-edit-mode-map 'risky-local-variable t) ;for Emacs 20.7

(defvar svn-log-edit-mode-menu) ;really defined with `easy-menu-define' below.

(defun svn-log-edit-common-setup ()
  (set (make-local-variable 'paragraph-start) svn-log-edit-paragraph-start)
  (set (make-local-variable 'paragraph-separate) svn-log-edit-paragraph-separate))

(if svn-log-edit-use-log-edit-mode
    (define-derived-mode svn-log-edit-mode log-edit-mode "svn-log-edit"
      "Wrapper around `log-edit-mode' for psvn.el"
      (easy-menu-add svn-log-edit-mode-menu)
      (setq svn-log-edit-update-log-entry nil)
      (set (make-local-variable 'log-edit-callback) 'svn-log-edit-done)
      (set (make-local-variable 'log-edit-listfun) 'svn-log-edit-files-to-commit)
      (set (make-local-variable 'log-edit-initial-files) (log-edit-files))
      (svn-log-edit-common-setup)
      (message "Press %s when you are done editing."
               (substitute-command-keys "\\[log-edit-done]"))
      )
  (defun svn-log-edit-mode ()
    "Major Mode to edit svn log messages.
Commands:
\\{svn-log-edit-mode-map}"
    (interactive)
    (kill-all-local-variables)
    (use-local-map svn-log-edit-mode-map)
    (easy-menu-add svn-log-edit-mode-menu)
    (setq major-mode 'svn-log-edit-mode)
    (setq mode-name "svn-log-edit")
    (setq svn-log-edit-update-log-entry nil)
    (svn-log-edit-common-setup)
    (run-hooks 'svn-log-edit-mode-hook)))

(when (not svn-log-edit-mode-map)
  (setq svn-log-edit-mode-map (make-sparse-keymap))
  (unless svn-log-edit-use-log-edit-mode
    (define-key svn-log-edit-mode-map (kbd "C-c C-c") 'svn-log-edit-done))
  (define-key svn-log-edit-mode-map (kbd "C-c C-d") 'svn-log-edit-svn-diff)
  (define-key svn-log-edit-mode-map (kbd "C-c C-s") 'svn-log-edit-save-message)
  (define-key svn-log-edit-mode-map (kbd "C-c C-i") 'svn-log-edit-svn-status)
  (define-key svn-log-edit-mode-map (kbd "C-c C-l") 'svn-log-edit-svn-log)
  (define-key svn-log-edit-mode-map (kbd "C-c C-?") 'svn-log-edit-show-files-to-commit)
  (define-key svn-log-edit-mode-map (kbd "C-c C-z") 'svn-log-edit-erase-edit-buffer)
  (define-key svn-log-edit-mode-map (kbd "C-c C-q") 'svn-log-edit-abort))

(easy-menu-define svn-log-edit-mode-menu svn-log-edit-mode-map
"'svn-log-edit-mode' menu"
                  '("SVN-Log"
                    ["Save to disk" svn-log-edit-save-message t]
                    ["Commit" svn-log-edit-done t]
                    ["Show Diff" svn-log-edit-svn-diff t]
                    ["Show Status" svn-log-edit-svn-status t]
                    ["Show Log" svn-log-edit-svn-log t]
                    ["Show files to commit" svn-log-edit-show-files-to-commit t]
                    ["Erase buffer" svn-log-edit-erase-edit-buffer]
                    ["Abort" svn-log-edit-abort t]))
(put 'svn-log-edit-mode-menu 'risky-local-variable t)

(defun svn-log-edit-abort ()
  (interactive)
  (bury-buffer)
  (set-window-configuration svn-status-pre-commit-window-configuration))

(defun svn-log-edit-done ()
  "Finish editing the log message and run svn commit."
  (interactive)
  (svn-status-save-some-buffers)
  (save-excursion
    (set-buffer (get-buffer svn-log-edit-buffer-name))
    (when svn-log-edit-insert-files-to-commit
      (svn-log-edit-remove-comment-lines))
    (when (fboundp 'set-buffer-file-coding-system)
      (set-buffer-file-coding-system svn-status-svn-file-coding-system nil))
    (when (or svn-log-edit-update-log-entry svn-status-files-to-commit)
      (setq svn-status-temp-file-to-remove
            (concat svn-status-temp-dir "svn-log-edit.txt" svn-temp-suffix))
      (write-region (point-min) (point-max) svn-status-temp-file-to-remove nil 1))
    (bury-buffer))
  (if svn-log-edit-update-log-entry
      (when (y-or-n-p "Update the log entry? ")
        ;;   svn propset svn:log --revprop -r11672 -F file
        (svn-run nil t 'propset "propset" "svn:log" "--revprop"
                     (concat "-r" svn-log-edit-update-log-entry)
                     "-F" svn-status-temp-file-to-remove)
        (save-excursion
          (set-buffer svn-process-buffer-name)
          (message "%s" (buffer-substring (point-min) (- (point-max) 1)))))
    (when svn-status-files-to-commit ; there are files to commit
      (setq svn-status-operated-on-dot
            (and (= 1 (length svn-status-files-to-commit))
                 (string= "." (svn-status-line-info->filename (car svn-status-files-to-commit)))))
      (svn-status-create-arg-file svn-status-temp-arg-file ""
                                  svn-status-files-to-commit "")
      (svn-run t t 'commit "commit"
                   (unless svn-status-recursive-commit "--non-recursive")
                   "--targets" svn-status-temp-arg-file
                   "-F" svn-status-temp-file-to-remove
                   (when (eq svn-status-svn-file-coding-system 'utf-8)
                     '("--encoding" "UTF-8"))
                   svn-status-default-commit-arguments))
    (set-window-configuration svn-status-pre-commit-window-configuration)
    (message "svn-log editing done")))

(defun svn-log-edit-svn-diff (arg)
  "Show the diff we are about to commit.
If ARG then show diff between some other version of the selected files."
  (interactive "P")
  (set-buffer svn-status-buffer-name)   ; TODO: is this necessary?
  ;; This call is very much like `svn-status-show-svn-diff-for-marked-files'
  ;; but uses commit-specific variables instead of the current marks.
  (svn-status-show-svn-diff-internal svn-status-files-to-commit
                                     svn-status-recursive-commit
                                     (if arg :ask "BASE")))

(defun svn-log-edit-svn-log (arg)
  (interactive "P")
  (set-buffer svn-status-buffer-name)
  (svn-status-show-svn-log arg))

(defun svn-log-edit-svn-status ()
  (interactive)
  (pop-to-buffer svn-status-buffer-name)
  (other-window 1))

(defun svn-log-edit-files-to-commit ()
  (mapcar 'svn-status-line-info->filename svn-status-files-to-commit))

(defun svn-log-edit-show-files-to-commit ()
  (interactive)
  (message "Files to commit%s: %S"
           (if svn-status-recursive-commit " recursively" "")
           (svn-log-edit-files-to-commit)))

(defun svn-log-edit-save-message ()
  "Save the current log message to the file `svn-log-edit-file-name'."
  (interactive)
  (let ((log-edit-file-name (svn-log-edit-file-name)))
    (if (string= buffer-file-name log-edit-file-name)
        (save-buffer)
      (write-region (point-min) (point-max) log-edit-file-name))))

(defun svn-log-edit-erase-edit-buffer ()
  "Delete everything in the `svn-log-edit-buffer-name' buffer."
  (interactive)
  (set-buffer svn-log-edit-buffer-name)
  (erase-buffer))

(defun svn-log-edit-insert-files-to-commit ()
  (interactive)
  (svn-log-edit-remove-comment-lines)
  (let ((buf-size (- (point-max) (point-min))))
    (save-excursion
      (goto-char (point-min))
      (insert "## Lines starting with '## ' will be removed from the log message.\n")
      (insert "## File(s) to commit"
              (if svn-status-recursive-commit " recursively" "") ":\n")
      (let ((file-list svn-status-files-to-commit))
        (while file-list
          (insert (concat "## " (svn-status-line-info->filename (car file-list)) "\n"))
          (setq file-list (cdr file-list)))))
    (when (= 0 buf-size)
      (goto-char (point-max)))))

(defun svn-log-edit-remove-comment-lines ()
  (interactive)
  (save-excursion
    (goto-char (point-min))
    (flush-lines "^## .*")))

(defun svn-file-add-to-changelog (prefix-arg)
  "Create a changelog entry for the function at point.
The variable `svn-status-changelog-style' allows to select the used changlog style"
  (interactive "P")
  (cond ((eq svn-status-changelog-style 'changelog)
         (svn-file-add-to-log-changelog-style prefix-arg))
        ((eq svn-status-changelog-style 'svn-dev)
         (svn-file-add-to-log-svn-dev-style prefix-arg))
        ((fboundp svn-status-changelog-style)
         (funcall svn-status-changelog-style prefix-arg))
        (t
         (error "Invalid setting for `svn-status-changelog-style'"))))

(defun svn-file-add-to-log-changelog-style (curdir)
  "Create a changelog entry for the function at point.
`add-change-log-entry-other-window' creates the header information.
If CURDIR, save the log file in the current directory, otherwise in the base directory of this working copy."
  (interactive "P")
  (add-change-log-entry-other-window nil (svn-log-edit-file-name curdir))
  (svn-log-edit-mode))

;; taken from svn-dev.el: svn-log-path-derive
(defun svn-dev-log-path-derive (path)
  "Derive a relative directory path for absolute PATH, for a log entry."
  (save-match-data
    (let ((base (file-name-nondirectory path))
          (chop-spot (string-match
                      "\\(code/\\)\\|\\(src/\\)\\|\\(projects/\\)"
                      path)))
      (if chop-spot
          (progn
            (setq path (substring path (match-end 0)))
            ;; Kluge for Subversion developers.
            (if (string-match "subversion/" path)
                (substring path (+ (match-beginning 0) 11))
              path))
        (string-match (expand-file-name "~/") path)
        (substring path (match-end 0))))))

;; taken from svn-dev.el: svn-log-message
(defun svn-file-add-to-log-svn-dev-style (prefix-arg)
  "Add to an in-progress log message, based on context around point.
If PREFIX-ARG is negative, then use basenames only in
log messages, otherwise use full paths.  The current defun name is
always used.

If PREFIX-ARG is a list (e.g. by using C-u), save the log file in
the current directory, otherwise in the base directory of this
working copy.

If the log message already contains material about this defun, then put
point there, so adding to that material is easy.

Else if the log message already contains material about this file, put
point there, and push onto the kill ring the defun name with log
message dressing around it, plus the raw defun name, so yank and
yank-next are both useful.

Else if there is no material about this defun nor file anywhere in the
log message, then put point at the end of the message and insert a new
entry for file with defun.
"
  (interactive "P")
  (let* ((short-file-names (and (numberp prefix-arg) (< prefix-arg 0)))
         (curdir (listp prefix-arg))
         (this-file (if short-file-names
                        (file-name-nondirectory buffer-file-name)
                      (svn-dev-log-path-derive buffer-file-name)))
         (this-defun (or (add-log-current-defun)
                         (save-excursion
                           (save-match-data
                             (if (eq major-mode 'c-mode)
                                 (progn
                                   (if (fboundp 'c-beginning-of-statement-1)
                                       (c-beginning-of-statement-1)
                                     (c-beginning-of-statement))
                                   (search-forward "(" nil t)
                                   (forward-char -1)
                                   (forward-sexp -1)
                                   (buffer-substring
                                    (point)
                                    (progn (forward-sexp 1) (point)))))))))
         (log-file (svn-log-edit-file-name curdir)))
    (find-file log-file)
    (goto-char (point-min))
    ;; Strip text properties from strings
    (set-text-properties 0 (length this-file) nil this-file)
    (set-text-properties 0 (length this-defun) nil this-defun)
    ;; If log message for defun already in progress, add to it
    (if (and
         this-defun                        ;; we have a defun to work with
         (search-forward this-defun nil t) ;; it's in the log msg already
         (save-excursion                   ;; and it's about the same file
           (save-match-data
             (if (re-search-backward  ; Ick, I want a real filename regexp!
                  "^\\*\\s-+\\([a-zA-Z0-9-_.@=+^$/%!?(){}<>]+\\)" nil t)
                 (string-equal (match-string 1) this-file)
               t))))
        (if (re-search-forward ":" nil t)
            (if (looking-at " ") (forward-char 1)))
      ;; Else no log message for this defun in progress...
      (goto-char (point-min))
      ;; But if log message for file already in progress, add to it.
      (if (search-forward this-file nil t)
          (progn
            (if this-defun (progn
                             (kill-new (format "(%s): " this-defun))
                             (kill-new this-defun)))
            (search-forward ")" nil t)
            (if (looking-at " ") (forward-char 1)))
        ;; Found neither defun nor its file, so create new entry.
        (goto-char (point-max))
        (if (not (bolp)) (insert "\n"))
        (insert (format "\n* %s (%s): " this-file (or this-defun "")))
        ;; Finally, if no derived defun, put point where the user can
        ;; type it themselves.
        (if (not this-defun) (forward-char -3))))))

;; --------------------------------------------------------------------------------
;; svn-log-view-mode:
;; --------------------------------------------------------------------------------

(defvar svn-log-view-mode-map () "Keymap used in `svn-log-view-mode' buffers.")
(put 'svn-log-view-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-log-view-mode-map)
  (setq svn-log-view-mode-map (make-sparse-keymap))
  (suppress-keymap svn-log-view-mode-map)
  (define-key svn-log-view-mode-map (kbd "p") 'svn-log-view-prev)
  (define-key svn-log-view-mode-map (kbd "n") 'svn-log-view-next)
  (define-key svn-log-view-mode-map (kbd "~") 'svn-log-get-specific-revision)
  (define-key svn-log-view-mode-map (kbd "E") 'svn-log-ediff-specific-revision)
  (define-key svn-log-view-mode-map (kbd "=") 'svn-log-view-diff)
  (define-key svn-log-view-mode-map (kbd "TAB") 'svn-log-next-link)
  (define-key svn-log-view-mode-map [backtab] 'svn-log-prev-link)
  (define-key svn-log-view-mode-map (kbd "RET") 'svn-log-find-file-at-point)
  (define-key svn-log-view-mode-map (kbd "e") 'svn-log-edit-log-entry)
  (define-key svn-log-view-mode-map (kbd "q") 'bury-buffer))

(defvar svn-log-view-popup-menu-map ()
  "Keymap used to show popup menu in `svn-log-view-mode' buffers.")
(put 'svn-log-view-popup-menu-map 'risky-local-variable t) ;for Emacs 20.7
(when (not svn-log-view-popup-menu-map)
  (setq svn-log-view-popup-menu-map (make-sparse-keymap))
  (suppress-keymap svn-log-view-popup-menu-map)
  (define-key svn-log-view-popup-menu-map [down-mouse-3] 'svn-log-view-popup-menu))

(easy-menu-define svn-log-view-mode-menu svn-log-view-mode-map
"'svn-log-view-mode' menu"
                  '("SVN-LogView"
                    ["Show Changeset" svn-log-view-diff t]
                    ["Ediff file at point" svn-log-ediff-specific-revision t]
                    ["Find file at point" svn-log-find-file-at-point t]
                    ["Get older revision for file at point" svn-log-get-specific-revision t]
                    ["Edit log message" svn-log-edit-log-entry t]))

(defun svn-log-view-popup-menu (event)
  (interactive "e")
  (mouse-set-point event)
  (let* ((rev (svn-log-revision-at-point)))
    (when rev
      (svn-status-face-set-temporary-during-popup
       'svn-status-marked-popup-face (svn-point-at-bol) (svn-point-at-eol)
       svn-log-view-mode-menu))))

(defvar svn-log-view-font-lock-basic-keywords
  '(("^r[0-9]+ .+" (0 `(face font-lock-keyword-face
                        mouse-face highlight
                        keymap ,svn-log-view-popup-menu-map))))
  "Basic keywords in `svn-log-view-mode'.")
(put 'svn-log-view-font-basic-lock-keywords 'risky-local-variable t) ;for Emacs 20.7

(defvar svn-log-view-font-lock-keywords)
(define-derived-mode svn-log-view-mode fundamental-mode "svn-log-view"
  "Major Mode to show the output from svn log.
Commands:
\\{svn-log-view-mode-map}
"
  (use-local-map svn-log-view-mode-map)
  (easy-menu-add svn-log-view-mode-menu)
  (set (make-local-variable 'svn-log-view-font-lock-keywords) svn-log-view-font-lock-basic-keywords)
  (dolist (lh svn-log-link-handlers)
    (add-to-list 'svn-log-view-font-lock-keywords (gethash lh svn-log-registered-link-handlers)))
  (set (make-local-variable 'font-lock-defaults) '(svn-log-view-font-lock-keywords t)))

(defun svn-log-view-next ()
  (interactive)
  (when (re-search-forward "^r[0-9]+" nil t)
    (beginning-of-line 2)
    (unless (looking-at "Changed paths:")
      (beginning-of-line 1))))

(defun svn-log-view-prev ()
  (interactive)
  (when (re-search-backward "^r[0-9]+" nil t 2)
    (beginning-of-line 2)
    (unless (looking-at "Changed paths:")
      (beginning-of-line 1))))

(defun svn-log-revision-at-point ()
  (save-excursion
    (end-of-line)
    (re-search-backward "^r\\([0-9]+\\)")
    (svn-match-string-no-properties 1)))

(defun svn-log-file-name-at-point (respect-checkout-prefix-path)
  (let ((full-file-name)
        (file-name)
        (checkout-prefix-path (if respect-checkout-prefix-path
                                  (url-unhex-string
                                   (svn-status-checkout-prefix-path))
                                "")))
    (save-excursion
      (beginning-of-line)
      (when (looking-at "   [MA] /\\(.+\\)$")
        (setq full-file-name (svn-match-string-no-properties 1))))
    (when (string= checkout-prefix-path "")
      (setq checkout-prefix-path "/"))
    (if (null full-file-name)
        (progn
          (message "No file at point")
          nil)
      (setq file-name
            (if (eq (string-match (regexp-quote (substring checkout-prefix-path 1)) full-file-name) 0)
                (substring full-file-name (- (length checkout-prefix-path) (if (string= checkout-prefix-path "/") 1 0)))
              full-file-name))
      ;; (message "svn-log-file-name-at-point %s prefix: '%s', full-file-name: %s" file-name checkout-prefix-path full-file-name)
      file-name)))

(defun svn-log-find-file-at-point ()
  (interactive)
  (let ((file-name (svn-log-file-name-at-point t)))
    (when file-name
      (let ((default-directory (svn-status-base-dir)))
        ;;(message "svn-log-file-name-at-point: %s, default-directory: %s" file-name default-directory)
        (find-file file-name)))))

(defun svn-log-next-link ()
  "Jump to the next external link in this buffer"
  (interactive)
  (let ((start-pos (if (get-text-property (point) 'link-handler)
                       (next-single-property-change (point) 'link-handler)
                     (point))))
    (goto-char (or (next-single-property-change start-pos 'link-handler) (point)))))

(defun svn-log-prev-link ()
  "Jump to the previous external link in this buffer"
  (interactive)
  (let ((start-pos (if (get-text-property (point) 'link-handler)
                       (previous-single-property-change (point) 'link-handler)
                     (point))))
    (goto-char (or (previous-single-property-change (or start-pos (point)) 'link-handler) (point)))))

(defun svn-log-view-diff (arg)
  "Show the changeset for a given log entry.
When called with a prefix argument, ask the user for the revision."
  (interactive "P")
  (svn-status-diff-show-changeset (svn-log-revision-at-point) arg))

(defun svn-log-get-specific-revision ()
  "Get an older revision of the file at point via svn cat."
  (interactive)
  ;; (message "%S" (svn-status-make-line-info (svn-log-file-name-at-point t)))
  (let ((default-directory (svn-status-base-dir)))
    (svn-status-get-specific-revision-internal
     (list (svn-status-make-line-info (svn-log-file-name-at-point t)))
     (svn-log-revision-at-point)
     nil)))

(defun svn-log-ediff-specific-revision ()
  "Call ediff for the file at point to view a changeset"
  (interactive)
  ;; (message "svn-log-ediff-specific-revision: %s" (svn-log-file-name-at-point t))
  (let* ((cur-buf (current-buffer))
         (upper-rev (svn-log-revision-at-point))
         (lower-rev (number-to-string (- (string-to-number upper-rev) 1)))
         (file-name (svn-log-file-name-at-point t))
         (default-directory (svn-status-base-dir))
         (upper-rev-file-name (when file-name
                                (cdar (svn-status-get-specific-revision-internal
                                       (list (svn-status-make-line-info file-name)) upper-rev nil))))
         (lower-rev-file-name (when file-name
                                (cdar (svn-status-get-specific-revision-internal
                                       (list (svn-status-make-line-info file-name)) lower-rev nil)))))
    ;;(message "%S %S" upper-rev-file-name lower-rev-file-name)
    (if file-name
        (let* ((ediff-after-quit-destination-buffer cur-buf)
               (newer-buffer (find-file-noselect upper-rev-file-name))
               (base-buff (find-file-noselect lower-rev-file-name))
               (svn-transient-buffers (list base-buff newer-buffer))
               (startup-hook '(svn-ediff-startup-hook)))
          (ediff-buffers base-buff newer-buffer startup-hook))
      (message "No file at point"))))

(defun svn-log-edit-log-entry ()
  "Edit the given log entry."
  (interactive)
  (let ((rev (svn-log-revision-at-point))
        (log-message))
    (svn-run nil t 'propget-parse "propget" "--revprop" (concat "-r" rev) "svn:log")
    (save-excursion
      (set-buffer svn-process-buffer-name)
      (setq log-message (if (> (point-max) 1)
                            (buffer-substring (point-min) (- (point-max) 1))
                          "")))
    (svn-status-pop-to-commit-buffer)
    ;; If the buffer has been narrowed, `svn-log-edit-done' will use
    ;; only the accessible part.  So we need not erase the rest here.
    (delete-region (point-min) (point-max))
    (insert log-message)
    (goto-char (point-min))
    (setq svn-log-edit-update-log-entry rev)))


;; allow additional hyperlinks in log view buffers
(defvar svn-log-link-keymap ()
  "Keymap used to resolve links `svn-log-view-mode' buffers.")
(put 'svn-log-link-keymap 'risky-local-variable t) ;for Emacs 20.7
(when (not svn-log-link-keymap)
  (setq svn-log-link-keymap (make-sparse-keymap))
  (suppress-keymap svn-log-link-keymap)
  (define-key svn-log-link-keymap [mouse-2] 'svn-log-resolve-mouse-link)
  (define-key svn-log-link-keymap (kbd "RET") 'svn-log-resolve-link))

(defun svn-log-resolve-mouse-link (event)
  (interactive "e")
  (mouse-set-point event)
  (svn-log-resolve-link))

(defun svn-log-resolve-link ()
  (interactive)
  (let* ((point-adjustment (if (not (get-text-property (- (point) 1) 'link-handler)) 1
                             (if (not (get-text-property (+ (point) 1) 'link-handler)) -1 0)))
         (link-name (buffer-substring-no-properties (previous-single-property-change (+ (point) point-adjustment) 'link-handler)
                                                   (next-single-property-change (+ (point) point-adjustment) 'link-handler))))
    ;; (message "svn-log-resolve-link '%s'" link-name)
    (funcall (get-text-property (point) 'link-handler) link-name)))

(defun svn-log-register-link-handler (handler-id link-regexp handler-function)
  "Register a link handler for external links in *svn-log* buffers
HANDLER-ID is a symbolic name for this handler. The link handler is active when HANDLER-ID
is registered in `svn-log-link-handlers'.
LINK-REGEXP specifies a regular expression that matches the external link.
HANDLER-FUNCTION is called with the match of LINK-REGEXP when the user clicks at the external link."
  (let ((font-lock-desc (list link-regexp '(0 `(face font-lock-function-name-face
                                            mouse-face highlight
                                            link-handler invalid-handler-function
                                            keymap ,svn-log-link-keymap)))))
    ;; no idea, how to use handler-function in invalid-handler-function above, so set it here
    (setcar (nthcdr 5 (nth 1 (nth 1 (nth 1 font-lock-desc)))) handler-function)
    (svn-puthash handler-id font-lock-desc svn-log-registered-link-handlers)))

;; example: add support for ditrack links and handle them via svn-log-resolve-ditrack
;;(svn-log-register-link-handler 'ditrack-issue "i#[0-9]+" 'svn-log-resolve-ditrack)
;;(defun svn-log-resolve-ditrack (link-name)
;;  (interactive)
;;  (message "svn-log-resolve-ditrack %s" link-name))


(defun svn-log-resolve-trac-ticket-short (link-name)
  "Show the trac ticket specified by LINK-NAME via `svn-trac-browse-ticket'."
  (interactive)
  (let ((ticket-nr (string-to-number (svn-substring-no-properties link-name 1))))
    (svn-trac-browse-ticket ticket-nr)))

;; register the out of the box provided link handlers
(svn-log-register-link-handler 'trac-ticket-short "#[0-9]+" 'svn-log-resolve-trac-ticket-short)

;; the actually used link handlers are specified in svn-log-link-handlers

;; --------------------------------------------------------------------------------
;; svn-info-mode
;; --------------------------------------------------------------------------------
(defvar svn-info-mode-map () "Keymap used in `svn-info-mode' buffers.")
(put 'svn-info-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-info-mode-map)
  (setq svn-info-mode-map (make-sparse-keymap))
  (define-key svn-info-mode-map [?s] 'svn-status-pop-to-status-buffer)
  (define-key svn-info-mode-map (kbd "h") 'svn-status-pop-to-partner-buffer)
  (define-key svn-info-mode-map (kbd "n") 'next-line)
  (define-key svn-info-mode-map (kbd "p") 'previous-line)
  (define-key svn-info-mode-map (kbd "RET") 'svn-info-show-context)
  (define-key svn-info-mode-map [?q] 'bury-buffer))

(defun svn-info-mode ()
  "Major Mode to view informative output from svn."
  (interactive)
  (kill-all-local-variables)
  (use-local-map svn-info-mode-map)
  (setq major-mode 'svn-info-mode)
  (setq mode-name "svn-info")
  (toggle-read-only 1))

(defun svn-info-show-context ()
  "Show the context for a line in the info buffer.
Currently is the output from the svn update command known."
  (interactive)
  (cond ((save-excursion
           (goto-char (point-max))
           (forward-line -1)
           (beginning-of-line)
           (looking-at "Updated to revision"))
         ;; svn-info contains info from an svn update
         (let ((cur-pos (point))
               (file-name (buffer-substring-no-properties
                           (progn (beginning-of-line) (re-search-forward ".. +") (point))
                           (line-end-position)))
               (pos))
           (when (eq system-type 'windows-nt)
             (setq file-name (replace-regexp-in-string "\\\\" "/" file-name)))
           (goto-char cur-pos)
           (with-current-buffer svn-status-buffer-name
             (setq pos (svn-status-get-file-name-buffer-position file-name)))
           (when pos
             (svn-status-pop-to-new-partner-buffer svn-status-buffer-name)
             (goto-char pos))))))

;; --------------------------------------------------------------------------------
;; svn blame minor mode
;; --------------------------------------------------------------------------------

(unless (assq 'svn-blame-mode minor-mode-alist)
  (setq minor-mode-alist
        (cons (list 'svn-blame-mode " SvnBlame")
              minor-mode-alist)))

(defvar svn-blame-mode-map () "Keymap used in `svn-blame-mode' buffers.")
(put 'svn-blame-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-blame-mode-map)
  (setq svn-blame-mode-map (make-sparse-keymap))
  (define-key svn-blame-mode-map [?s] 'svn-status-pop-to-status-buffer)
  (define-key svn-blame-mode-map (kbd "n") 'next-line)
  (define-key svn-blame-mode-map (kbd "p") 'previous-line)
  (define-key svn-blame-mode-map (kbd "RET") 'svn-blame-open-source-file)
  (define-key svn-blame-mode-map (kbd "a") 'svn-blame-highlight-author)
  (define-key svn-blame-mode-map (kbd "r") 'svn-blame-highlight-revision)
  (define-key svn-blame-mode-map (kbd "=") 'svn-blame-show-changeset)
  (define-key svn-blame-mode-map (kbd "l") 'svn-blame-show-log)
  (define-key svn-blame-mode-map [?q] 'bury-buffer))

(easy-menu-define svn-blame-mode-menu svn-blame-mode-map
"svn blame minor mode menu"
                  '("SvnBlame"
                    ["Jump to source location" svn-blame-open-source-file t]
                    ["Show changeset" svn-blame-show-changeset t]
                    ["Show log" svn-blame-show-log t]
                    ["Highlight by author" svn-blame-highlight-author t]
                    ["Highlight by revision" svn-blame-highlight-revision t]))

(or (assq 'svn-blame-mode minor-mode-map-alist)
    (setq minor-mode-map-alist
          (cons (cons 'svn-blame-mode svn-blame-mode-map) minor-mode-map-alist)))

(make-variable-buffer-local 'svn-blame-mode)

(defun svn-blame-mode (&optional arg)
  "Toggle svn blame minor mode.
With ARG, turn svn blame minor mode on if ARG is positive, off otherwise.

Note: This mode does not yet work on XEmacs...
It is probably because the revisions are in 'before-string properties of overlays

Key bindings:
\\{svn-blame-mode-map}"
  (interactive "P")
  (setq svn-blame-mode (if (null arg)
                           (not svn-blame-mode)
                         (> (prefix-numeric-value arg) 0)))
  (if svn-blame-mode
      (progn
        (easy-menu-add svn-blame-mode-menu)
        (toggle-read-only 1))
    (easy-menu-remove svn-blame-mode-menu))
  (force-mode-line-update))

(defun svn-status-activate-blame-mode ()
  "Activate the svn blame minor in the current buffer.
The current buffer must contain a valid output from svn blame"
  (save-excursion
    (goto-char (point-min))
    (let ((buffer-read-only nil)
          (line (svn-line-number-at-pos))
          (limit (point-max))
          (info-end-col (save-excursion (forward-word 2) (+ (current-column) 1)))
          (s)
          ov)
      ;; remove the old overlays (only for testing)
      ;; (dolist (ov (overlays-in (point) limit))
      ;;   (when (overlay-get ov 'svn-blame-line-info)
      ;;     (delete-overlay ov)))
      (while (and (not (eobp)) (< (point) limit))
        (setq ov (make-overlay (point) (point)))
        (overlay-put ov 'svn-blame-line-info t)
        (setq s (buffer-substring-no-properties (svn-point-at-bol) (+ (svn-point-at-bol) info-end-col)))
        (overlay-put ov 'before-string (propertize s 'face 'svn-status-blame-rev-number-face))
        (overlay-put ov 'rev-info (delete "" (split-string s " ")))
        (delete-region (svn-point-at-bol) (+ (svn-point-at-bol) info-end-col))
        (forward-line)
        (setq line (1+ line)))))
  (let* ((buf-name (format "*svn-blame: %s*" (file-relative-name svn-status-blame-file-name)))
         (buffer (get-buffer buf-name)))
    (when buffer
      (kill-buffer buffer))
    (rename-buffer buf-name))
  ;; use the correct mode for the displayed blame output
  (let ((buffer-file-name svn-status-blame-file-name))
    (normal-mode)
    (set (make-local-variable 'svn-status-blame-file-name) svn-status-blame-file-name))
  (font-lock-fontify-buffer)
  (svn-blame-mode 1))

(defun svn-blame-open-source-file ()
  "Jump to the source file location for the current position in the svn blame buffer"
  (interactive)
  (let ((src-line-number (svn-line-number-at-pos))
        (src-line-col (current-column)))
    (find-file-other-window svn-status-blame-file-name)
    (goto-line src-line-number)
    (forward-char src-line-col)))

(defun svn-blame-rev-at-point ()
  (let ((rev))
    (dolist (ov (overlays-in (svn-point-at-bol) (line-end-position)))
      (when (overlay-get ov 'svn-blame-line-info)
        (setq rev (car (overlay-get ov 'rev-info)))))
    rev))

(defun svn-blame-show-changeset (arg)
  "Show a diff for the revision at point.
When called with a prefix argument, allow the user to edit the revision."
  (interactive "P")
  (svn-status-diff-show-changeset (svn-blame-rev-at-point) arg))

(defun svn-blame-show-log (arg)
  "Show the log for the revision at point.
The output is put into the *svn-log* buffer
The optional prefix argument ARG determines which switches are passed to `svn log':
 no prefix               --- use whatever is in the list `svn-status-default-log-arguments'
 prefix argument of -1:  --- use the -q switch (quiet)
 prefix argument of 0    --- use no arguments
 other prefix arguments: --- use the -v switch (verbose)"
  (interactive "P")
  (let ((switches (svn-status-svn-log-switches arg))
        (rev (svn-blame-rev-at-point)))
    (svn-run t t 'log "log" "--revision" rev switches)))

(defun svn-blame-highlight-line-maybe (compare-func)
  (let ((reference-value)
        (is-highlighted)
        (consider-this-line)
        (hl-ov))
    (dolist (ov (overlays-in (svn-point-at-bol) (line-end-position)))
      (when (overlay-get ov 'svn-blame-line-info)
        (setq reference-value (funcall compare-func ov)))
      (when (overlay-get ov 'svn-blame-highlighted)
        (setq is-highlighted t)))
    (save-excursion
      (goto-char (point-min))
      (while (not (eobp))
        (setq consider-this-line nil)
        (dolist (ov (overlays-in (svn-point-at-bol) (line-end-position)))
          (when (overlay-get ov 'svn-blame-line-info)
            (when (string= reference-value (funcall compare-func ov))
              (setq consider-this-line t))))
        (when consider-this-line
          (dolist (ov (overlays-in (svn-point-at-bol) (line-end-position)))
            (when (and (overlay-get ov 'svn-blame-highlighted) is-highlighted)
              (delete-overlay ov))
            (unless is-highlighted
              (setq hl-ov (make-overlay (svn-point-at-bol) (line-end-position)))
              (overlay-put hl-ov 'svn-blame-highlighted t)
              (overlay-put hl-ov 'face 'svn-status-blame-highlight-face))))
        (forward-line)))))

(defun svn-blame-highlight-author-field (ov)
  (cadr (overlay-get ov 'rev-info)))

(defun svn-blame-highlight-author ()
  "(Un)Highlight all lines with the same author."
  (interactive)
  (svn-blame-highlight-line-maybe 'svn-blame-highlight-author-field))

(defun svn-blame-highlight-revision-field (ov)
  (car (overlay-get ov 'rev-info)))

(defun svn-blame-highlight-revision ()
  "(Un)Highlight all lines with the same revision."
  (interactive)
  (svn-blame-highlight-line-maybe 'svn-blame-highlight-revision-field))

;; --------------------------------------------------------------------------------
;; svn-process-mode
;; --------------------------------------------------------------------------------
(defvar svn-process-mode-map () "Keymap used in `svn-process-mode' buffers.")
(put 'svn-process-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-process-mode-map)
  (setq svn-process-mode-map (make-sparse-keymap))
  (define-key svn-process-mode-map (kbd "RET") 'svn-process-send-string-and-newline)
  (define-key svn-process-mode-map [?s] 'svn-process-send-string)
  (define-key svn-process-mode-map [?q] 'bury-buffer))

(easy-menu-define svn-process-mode-menu svn-process-mode-map
"'svn-process-mode' menu"
                  '("SvnProcess"
                    ["Send line to process" svn-process-send-string-and-newline t]
                    ["Send raw string to process" svn-process-send-string t]
                    ["Bury process buffer" bury-buffer t]))

(defun svn-process-mode ()
  "Major Mode to view process output from svn.

You can send a new line terminated string to the process via \\[svn-process-send-string-and-newline]
You can send raw data to the process via \\[svn-process-send-string]."
  (interactive)
  (kill-all-local-variables)
  (use-local-map svn-process-mode-map)
  (easy-menu-add svn-log-view-mode-menu)
  (setq major-mode 'svn-process-mode)
  (setq mode-name "svn-process"))

;; --------------------------------------------------------------------------------
;; svn status persistent options
;; --------------------------------------------------------------------------------

(defun svn-status-repo-for-path (directory)
  "Find the repository root for DIRECTORY."
  (let ((old-process-default-dir))
    (with-current-buffer (get-buffer-create svn-process-buffer-name)
      (setq old-process-default-dir default-directory)
      (setq default-directory directory)) ;; update the default-directory for the *svn-process* buffer
  (svn-run nil t 'parse-info "info" ".")
  (with-current-buffer svn-process-buffer-name
    ;; (message "svn-status-repo-for-path: %s: default-directory: %s directory: %s old-process-default-dir: %s" svn-process-buffer-name default-directory directory old-process-default-dir)
    (setq default-directory old-process-default-dir)
    (goto-char (point-min))
    (let ((case-fold-search t))
      (if (search-forward "repository root: " nil t)
          (buffer-substring-no-properties (point) (svn-point-at-eol))
        (when (search-forward "repository uuid: " nil t)
          (message "psvn.el: Detected an old svn working copy in '%s'. Please check it out again to get a 'Repository Root' entry in the svn info output."
                   default-directory)
          (concat "Svn Repo UUID: " (buffer-substring-no-properties (point) (svn-point-at-eol)))))))))

(defun svn-status-base-dir (&optional start-directory)
  "Find the svn root directory for the current working copy.
Return nil, if not in a svn working copy."
  (let* ((start-dir (expand-file-name (or start-directory default-directory)))
         (base-dir (gethash start-dir svn-status-base-dir-cache 'not-found)))
    ;;(message "svn-status-base-dir: %S %S" start-dir base-dir)
    (if (not (eq base-dir 'not-found))
        base-dir
      ;; (message "calculating base-dir for %s" start-dir)
      (unless svn-client-version
        (svn-status-version))
      (let* ((base-dir start-dir)
             (repository-root (svn-status-repo-for-path base-dir))
             (dot-svn-dir (concat base-dir (svn-wc-adm-dir-name)))
             (in-tree (and repository-root (file-exists-p dot-svn-dir)))
             (dir-below (expand-file-name base-dir)))
        ;; (message "repository-root: %s start-dir: %s" repository-root start-dir)
        (if (and (<= (car svn-client-version) 1) (< (cadr svn-client-version) 3))
            (setq base-dir (svn-status-base-dir-for-ancient-svn-client start-dir)) ;; svn version < 1.3
          (while (when (and dir-below (file-exists-p dot-svn-dir))
                   (setq base-dir (file-name-directory dot-svn-dir))
                   (string-match "\\(.+/\\).+/" dir-below)
                   (setq dir-below
                         (and (string-match "\\(.*/\\)[^/]+/" dir-below)
                              (match-string 1 dir-below)))
                   ;; (message "base-dir: %s, dir-below: %s, dot-svn-dir: %s in-tree: %s" base-dir dir-below dot-svn-dir in-tree)
                   (when dir-below
                     (if (string= (svn-status-repo-for-path dir-below) repository-root)
                         (setq dot-svn-dir (concat dir-below (svn-wc-adm-dir-name)))
                       (setq dir-below nil)))))
          (setq base-dir (and in-tree base-dir)))
        (svn-puthash start-dir base-dir svn-status-base-dir-cache)
        (svn-status-message 7 "svn-status-base-dir %s => %s" start-dir base-dir)
        base-dir))))

(defun svn-status-base-dir-for-ancient-svn-client (&optional start-directory)
  "Find the svn root directory for the current working copy.
Return nil, if not in a svn working copy.
This function is used for svn clients version 1.2 and below."
  (let* ((base-dir (expand-file-name (or start-directory default-directory)))
         (dot-svn-dir (concat base-dir (svn-wc-adm-dir-name)))
         (in-tree (file-exists-p dot-svn-dir))
         (dir-below (expand-file-name default-directory)))
    (while (when (and dir-below (file-exists-p dot-svn-dir))
             (setq base-dir (file-name-directory dot-svn-dir))
             (string-match "\\(.+/\\).+/" dir-below)
             (setq dir-below
                   (and (string-match "\\(.*/\\)[^/]+/" dir-below)
                        (match-string 1 dir-below)))
             (setq dot-svn-dir (concat dir-below (svn-wc-adm-dir-name)))))
    (and in-tree base-dir)))

(defun svn-status-save-state ()
  "Save psvn persistent options for this working copy to a file."
  (interactive)
  (let ((buf (find-file (concat (svn-status-base-dir) "++psvn.state"))))
    (erase-buffer)        ;Widen, because we'll save the whole buffer.
    ;; TO CHECK: why is svn-status-options a global variable??
    (setq svn-status-options
          (list
           (list "svn-trac-project-root" svn-trac-project-root)
           (list "sort-status-buffer" svn-status-sort-status-buffer)
           (list "elide-list" svn-status-elided-list)
           (list "module-name" svn-status-module-name)
           (list "branch-list" svn-status-branch-list)
           (list "changelog-style" svn-status-changelog-style)
           ))
    (insert (pp-to-string svn-status-options))
    (save-buffer)
    (kill-buffer buf)))

(defun svn-status-load-state (&optional no-error)
  "Load psvn persistent options for this working copy from a file."
  (interactive)
  (let ((file (concat (svn-status-base-dir) "++psvn.state")))
    (if (file-readable-p file)
        (with-temp-buffer
          (insert-file-contents file)
          (setq svn-status-options (read (current-buffer)))
          (setq svn-status-sort-status-buffer
                (nth 1 (assoc "sort-status-buffer" svn-status-options)))
          (setq svn-trac-project-root
                (nth 1 (assoc "svn-trac-project-root" svn-status-options)))
          (setq svn-status-elided-list
                (nth 1 (assoc "elide-list" svn-status-options)))
          (setq svn-status-module-name
                (nth 1 (assoc "module-name" svn-status-options)))
          (setq svn-status-branch-list
                (nth 1 (assoc "branch-list" svn-status-options)))
          (setq svn-status-changelog-style
                (nth 1 (assoc "changelog-style" svn-status-options)))
          (when (and (interactive-p) svn-status-elided-list (svn-status-apply-elide-list)))
          (message "psvn.el: loaded %s" file))
      (if no-error
          (setq svn-trac-project-root nil
                svn-status-elided-list nil
                svn-status-module-name nil
                svn-status-branch-list nil
                svn-status-changelog-style 'changelog)
        (error "psvn.el: %s is not readable." file)))))

(defun svn-status-toggle-sort-status-buffer ()
  "Toggle sorting of the *svn-status* buffer.

If you turn off sorting, you can speed up \\[svn-status].  However,
the buffer is not correctly sorted then.  This function will be
removed again, when a faster parsing and display routine for
`svn-status' is available."
  (interactive)
  (setq svn-status-sort-status-buffer (not svn-status-sort-status-buffer))
  (message "The %s buffer will %sbe sorted." svn-status-buffer-name
           (if svn-status-sort-status-buffer "" "not ")))

(defun svn-status-toggle-svn-verbose-flag ()
  "Toggle `svn-status-verbose'. "
  (interactive)
  (setq svn-status-verbose (not svn-status-verbose))
  (message "svn status calls will %suse the -v flag." (if svn-status-verbose "" "not ")))

(defun svn-status-toggle-display-full-path ()
  "Toggle displaying the full path in the `svn-status-buffer-name' buffer"
  (interactive)
  (setq svn-status-display-full-path (not svn-status-display-full-path))
  (message "The %s buffer will%s use full path names." svn-status-buffer-name
           (if svn-status-display-full-path "" " not"))
  (svn-status-update-buffer))

(defun svn-status-set-trac-project-root ()
  (interactive)
  (setq svn-trac-project-root
        (read-string "Trac project root (e.g.: http://projects.edgewall.com/trac/): "
                     svn-trac-project-root))
  (when (yes-or-no-p "Save the new setting for svn-trac-project-root to disk? ")
    (svn-status-save-state)))

(defun svn-status-set-module-name ()
  "Interactively set `svn-status-module-name'."
  (interactive)
  (setq svn-status-module-name
        (read-string "Short Unit Name (e.g.: MyProject): "
                     svn-status-module-name))
  (when (yes-or-no-p "Save the new setting for svn-status-module-name to disk? ")
    (svn-status-save-state)))

(defun svn-status-set-changelog-style ()
  "Interactively set `svn-status-changelog-style'."
  (interactive)
  (setq svn-status-changelog-style
        (intern (funcall svn-status-completing-read-function "svn-status on directory: " '("changelog" "svn-dev" "other"))))
  (when (string= svn-status-changelog-style 'other)
      (setq svn-status-changelog-style (car (find-function-read))))
  (when (yes-or-no-p "Save the new setting for svn-status-changelog-style to disk? ")
    (svn-status-save-state)))

(defun svn-status-set-branch-list ()
  "Interactively set `svn-status-branch-list'."
  (interactive)
  (setq svn-status-branch-list
        (split-string (read-string "Branch list: "
                                   (mapconcat 'identity svn-status-branch-list " "))))
  (when (yes-or-no-p "Save the new setting for svn-status-branch-list to disk? ")
    (svn-status-save-state)))

(defun svn-browse-url (url)
  "Call `browse-url', using `svn-browse-url-function'."
  (let ((browse-url-browser-function (or svn-browse-url-function
                                         browse-url-browser-function)))
    (browse-url url)))

;; --------------------------------------------------------------------------------
;; svn status trac integration
;; --------------------------------------------------------------------------------
(defun svn-trac-browse-wiki ()
  "Open the trac wiki view for the current svn repository."
  (interactive)
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "wiki")))

(defun svn-trac-browse-timeline ()
  "Open the trac timeline view for the current svn repository."
  (interactive)
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "timeline")))

(defun svn-trac-browse-roadmap ()
  "Open the trac roadmap view for the current svn repository."
  (interactive)
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "roadmap")))

(defun svn-trac-browse-source ()
  "Open the trac source browser for the current svn repository."
  (interactive)
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "browser")))

(defun svn-trac-browse-report (arg)
  "Open the trac report view for the current svn repository.
When called with a prefix argument, display the given report number."
  (interactive "P")
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "report" (if (numberp arg) (format "/%s" arg) ""))))

(defun svn-trac-browse-changeset (changeset-nr)
  "Show a changeset in the trac issue tracker."
  (interactive (list (read-number "Browse changeset number: " (number-at-point))))
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "changeset/" (number-to-string changeset-nr))))

(defun svn-trac-browse-ticket (ticket-nr)
  "Show a ticket in the trac issue tracker."
  (interactive (list (read-number "Browse ticket number: " (number-at-point))))
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "ticket/" (number-to-string ticket-nr))))

;;;------------------------------------------------------------
;;; resolve conflicts using ediff
;;;------------------------------------------------------------
(defun svn-resolve-conflicts-ediff (&optional name-A name-B)
  "Invoke ediff to resolve conflicts in the current buffer.
The conflicts must be marked with rcsmerge conflict markers."
  (interactive)
  (let* ((found nil)
         (file-name (file-name-nondirectory buffer-file-name))
         (your-buffer (generate-new-buffer
                       (concat "*" file-name
                               " " (or name-A "WORKFILE") "*")))
         (other-buffer (generate-new-buffer
                        (concat "*" file-name
                                " " (or name-B "CHECKED-IN") "*")))
         (result-buffer (current-buffer)))
    (save-excursion
      (set-buffer your-buffer)
      (erase-buffer)
      (insert-buffer-substring result-buffer)
      (goto-char (point-min))
      (while (re-search-forward "^<<<<<<< .\\(mine\\|working\\)\n" nil t)
        (setq found t)
        (replace-match "")
        (if (not (re-search-forward "^=======\n" nil t))
            (error "Malformed conflict marker"))
        (replace-match "")
        (let ((start (point)))
          (if (not (re-search-forward "^>>>>>>> .\\(r[0-9]+\\|merge.*\\)\n" nil t))
              (error "Malformed conflict marker"))
          (delete-region start (point))))
      (if (not found)
          (progn
            (kill-buffer your-buffer)
            (kill-buffer other-buffer)
            (error "No conflict markers found")))
      (set-buffer other-buffer)
      (erase-buffer)
      (insert-buffer-substring result-buffer)
      (goto-char (point-min))
      (while (re-search-forward "^<<<<<<< .\\(mine\\|working\\)\n" nil t)
        (let ((start (match-beginning 0)))
          (if (not (re-search-forward "^=======\n" nil t))
              (error "Malformed conflict marker"))
          (delete-region start (point))
          (if (not (re-search-forward "^>>>>>>> .\\(r[0-9]+\\|merge.*\\)\n" nil t))
              (error "Malformed conflict marker"))
          (replace-match "")))
      (let ((config (current-window-configuration))
            (ediff-default-variant 'default-B))

        ;; Fire up ediff.

        (set-buffer (ediff-merge-buffers your-buffer other-buffer))

        ;; Ediff is now set up, and we are in the control buffer.
        ;; Do a few further adjustments and take precautions for exit.

        (make-local-variable 'svn-ediff-windows)
        (setq svn-ediff-windows config)
        (make-local-variable 'svn-ediff-result)
        (setq svn-ediff-result result-buffer)
        (make-local-variable 'ediff-quit-hook)
        (setq ediff-quit-hook
              (lambda ()
                (let ((buffer-A ediff-buffer-A)
                      (buffer-B ediff-buffer-B)
                      (buffer-C ediff-buffer-C)
                      (result svn-ediff-result)
                      (windows svn-ediff-windows))
                  (ediff-cleanup-mess)
                  (set-buffer result)
                  (erase-buffer)
                  (insert-buffer-substring buffer-C)
                  (kill-buffer buffer-A)
                  (kill-buffer buffer-B)
                  (kill-buffer buffer-C)
                  (set-window-configuration windows)
                  (message "Conflict resolution finished; you may save the buffer"))))
        (message "Please resolve conflicts now; exit ediff when done")
        nil))))

(defun svn-resolve-conflicts (filename)
  (let ((buff (find-file-noselect filename)))
    (if buff
        (progn (switch-to-buffer buff)
               (svn-resolve-conflicts-ediff))
      (error "can not open file %s" filename))))

(defun svn-status-resolve-conflicts ()
  "Resolve conflict in the selected file"
  (interactive)
  (let ((file-info (svn-status-get-line-information)))
    (or (and file-info
             (= ?C (svn-status-line-info->filemark file-info))
             (svn-resolve-conflicts
              (svn-status-line-info->full-path file-info)))
        (error "can not resolve conflicts at this point"))))


;; --------------------------------------------------------------------------------
;; Working with branches
;; --------------------------------------------------------------------------------

(defun svn-branch-select (&optional prompt)
  "Select a branch interactively from `svn-status-branch-list'"
  (interactive)
  (unless prompt
    (setq prompt "Select branch: "))
  (let* ((branch (funcall svn-status-completing-read-function prompt svn-status-branch-list))
         (directory)
         (base-url))
    (when (string-match "#\\(1#\\)?\\(.+\\)" branch)
      (setq directory (match-string 2 branch))
      (setq base-url (concat (svn-status-base-info->repository-root) "/" directory))
      (save-match-data
        (svn-status-parse-info t))
      (if (eq (length (match-string 1 branch)) 0)
          (setq branch base-url)
        (let ((svn-status-branch-list (svn-status-ls base-url t)))
          (setq branch (concat (svn-status-base-info->repository-root) "/"
                               directory "/"
                               (svn-branch-select (format "Select branch from '%s': " directory)))))))
    branch))

(defun svn-branch-diff (branch1 branch2)
  "Show the diff between two svn repository urls.
When called interactively, use `svn-branch-select' to choose two branches from `svn-status-branch-list'."
  (interactive
   (let* ((branch1 (svn-branch-select "svn diff branch1: "))
          (branch2 (svn-branch-select (format "svn diff %s against: " branch1))))
     (list branch1 branch2)))
  (svn-run t t 'diff "diff" svn-status-default-diff-arguments branch1 branch2))

;; --------------------------------------------------------------------------------
;; svnadmin interface
;; --------------------------------------------------------------------------------
(defun svn-admin-create (dir)
  "Run svnadmin create DIR."
  (interactive (list (expand-file-name
                      (svn-read-directory-name "Create a svn repository at: "
                                               svn-admin-default-create-directory nil nil))))
  (shell-command-to-string (concat "svnadmin create " dir))
  (setq svn-admin-last-repository-dir (concat "file://" dir))
  (message "Svn repository created at %s" dir)
  (run-hooks 'svn-admin-create-hook))

;; - Import an empty directory
;;   cd to an empty directory
;;   svn import -m "Initial import" . file:///home/stefan/svn_repos/WaldiConfig/trunk
(defun svn-admin-create-trunk-directory ()
  "Import an empty trunk directory to `svn-admin-last-repository-dir'.
Set `svn-admin-last-repository-dir' to the new created trunk url."
  (interactive)
  (let ((empty-temp-dir-name (make-temp-name svn-status-temp-dir)))
    (make-directory empty-temp-dir-name t)
    (setq svn-admin-last-repository-dir (concat svn-admin-last-repository-dir "/trunk"))
    (svn-run nil t 'import "import" "-m" "Created trunk directory"
                             empty-temp-dir-name svn-admin-last-repository-dir)
    (delete-directory empty-temp-dir-name)))

(defun svn-admin-start-import ()
  "Start to import the current working directory in a subversion repository.
The user is asked to perform the following two steps:
1. Create a local repository
2. Add a trunk directory to that repository

After that step the empty base directory (either the root directory or
the trunk directory of the selected repository) is checked out in the current
working directory."
  (interactive)
  (if (y-or-n-p "Create local repository? ")
      (progn
        (call-interactively 'svn-admin-create)
        (when (y-or-n-p "Add a trunk directory? ")
          (svn-admin-create-trunk-directory)))
    (setq svn-admin-last-repository-dir (read-string "Repository Url: ")))
  (svn-checkout svn-admin-last-repository-dir "."))

;; --------------------------------------------------------------------------------
;; svn status profiling
;; --------------------------------------------------------------------------------
;;; Note about profiling psvn:
;;  (load-library "elp")
;;  M-x elp-reset-all
;;  (elp-instrument-package "svn-")
;;  M-x svn-status
;;  M-x elp-results

(defun svn-status-elp-init ()
  (interactive)
  (require 'elp)
  (elp-reset-all)
  (elp-instrument-package "svn-")
  (message "Run the desired svn command (e.g. M-x svn-status), then use M-x elp-results."))

(defun svn-status-last-commands (&optional string-prefix)
  "Return a string with the last executed svn commands"
  (interactive)
  (unless string-prefix
    (setq string-prefix ""))
  (with-output-to-string
    (dolist (e (ring-elements svn-last-cmd-ring))
      (princ (format "%s%s: svn %s <%s>\n" string-prefix (nth 0 e) (mapconcat 'concat (nth 1 e) " ") (nth 2 e))))))

;; --------------------------------------------------------------------------------
;; reporting bugs
;; --------------------------------------------------------------------------------
(defun svn-insert-indented-lines (text)
  "Helper function to insert TEXT, indented by two characters."
  (dolist (line (split-string text "\n"))
    (insert (format "  %s\n" line))))

(defun svn-prepare-bug-report ()
  "Create the buffer *psvn-bug-report*. This buffer can be useful to debug problems with psvn.el"
  (interactive)
  (let* ((last-output-buffer-name (or svn-status-last-output-buffer-name svn-process-buffer-name))
         (last-svn-cmd-output (with-current-buffer last-output-buffer-name
                                (buffer-substring-no-properties (point-min) (point-max)))))
    (switch-to-buffer "*psvn-bug-report*")
    (delete-region (point-min) (point-max))
    (insert "This buffer holds some debug informations for psvn.el\n")
    (insert "Please enter a description of the observed and the wanted behaviour\n")
    (insert "and send it to the author (stefan@xsteve.at) to allow easier debugging\n\n")
    (insert "Revisions:\n")
    (svn-insert-indented-lines (svn-status-version))
    (insert "Language environment:\n")
    (dolist (elem (svn-process-environment))
      (when (member (car (split-string elem "=")) '("LC_MESSAGES" "LC_ALL" "LANG"))
        (insert (format "  %s\n" elem))))
    (insert "\nLast svn commands:\n")
    (svn-insert-indented-lines (svn-status-last-commands))
    (insert (format "\nContent of the <%s> buffer:\n" last-output-buffer-name))
    (svn-insert-indented-lines last-svn-cmd-output)
    (goto-char (point-min))))

;; --------------------------------------------------------------------------------
;; Make it easier to reload psvn, if a distribution has an older version
;; Just add the following to your .emacs:
;; (svn-prepare-for-reload)
;; (load "/path/to/psvn.el")

;; Note the above will only work, if the loaded psvn.el has already the
;; function svn-prepare-for-reload
;; If this is not the case, do the following:
;; (load "/path/to/psvn.el");;make svn-prepare-for-reload available
;; (svn-prepare-for-reload)
;; (load "/path/to/psvn.el");; update the keybindings
;; --------------------------------------------------------------------------------

(defvar svn-prepare-for-reload-dont-touch-list '() "A list of variables that should not be touched by `svn-prepare-for-reload'")
(defvar svn-prepare-for-reload-variables-list '(svn-global-keymap svn-status-diff-mode-map svn-global-trac-map svn-status-mode-map
                                                svn-status-mode-property-map svn-status-mode-extension-map
                                                svn-status-mode-options-map svn-status-mode-trac-map svn-status-mode-branch-map
                                                svn-log-edit-mode-map svn-log-view-mode-map
                                                svn-log-view-popup-menu-map svn-info-mode-map svn-blame-mode-map svn-process-mode-map)
  "A list of variables that should be set to nil via M-x `svn-prepare-for-reload'")
(defun svn-prepare-for-reload ()
  "This function resets some psvn.el variables to nil.
It makes reloading a newer version of psvn.el easier, if for example the used
GNU/Linux distribution uses an older version.

The variables specified in `svn-prepare-for-reload-variables-list' will be reseted by this function.

A variable will keep its value, if it is specified in `svn-prepare-for-reload-dont-touch-list'."
  (interactive)
  (dolist (var svn-prepare-for-reload-variables-list)
    (unless (member var svn-prepare-for-reload-dont-touch-list)
      (message (format "Resetting value of %s to nil" var)))
      (set var nil)))

(provide 'psvn)

;; Local Variables:
;; indent-tabs-mode: nil
;; End:
;;; psvn.el ends here
