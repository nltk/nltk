;;; psvn.el --- Subversion interface for emacs
;; Copyright (C) 2002-2006 by Stefan Reichoer

;; Author: Stefan Reichoer, <stefan@xsteve.at>
;; $Id: psvn.el 19287 2006-04-09 18:58:40Z xsteve $

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
;; freebsd5, red hat el3 with svn 1.2.3

;; psvn.el is an interface for the revision control tool subversion
;; (see http://subversion.tigris.org)
;; psvn.el provides a similar interface for subversion as pcl-cvs for cvs.
;; At the moment the following commands are implemented:
;;
;; M-x svn-status: run 'svn -status -v'
;; M-x svn-examine (like psvn.el cvs-examine) is alias for svn-status
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
;; D     - svn-status-rm                    run 'svn rm'
;; M-c   - svn-status-cleanup               run 'svn cleanup'
;; b     - svn-status-blame                 run 'svn blame'
;; X e   - svn-status-export                run 'svn export'
;; RET   - svn-status-find-file-or-examine-directory
;; ^     - svn-status-examine-parent
;; ~     - svn-status-get-specific-revision
;; E     - svn-status-ediff-with-revision
;; X X   - svn-status-resolve-conflicts
;; s     - svn-status-show-process-buffer
;; e     - svn-status-toggle-edit-cmd-flag
;; ?     - svn-status-toggle-hide-unknown
;; _     - svn-status-toggle-hide-unmodified
;; m     - svn-status-set-user-mark
;; u     - svn-status-unset-user-mark
;; $     - svn-status-toggle-elide
;; w     - svn-status-copy-filename-as-kill
;; DEL   - svn-status-unset-user-mark-backwards
;; * !   - svn-status-unset-all-usermarks
;; * ?   - svn-status-mark-unknown
;; * A   - svn-status-mark-added
;; * M   - svn-status-mark-modified
;; * D   - svn-status-mark-deleted
;; * *   - svn-status-mark-changed
;; .     - svn-status-goto-root-or-return
;; f     - svn-status-find-file
;; o     - svn-status-find-file-other-window
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
;; P y   - svn-status-property-set-eol-style
;; P x   - svn-status-property-set-executable
;; h     - svn-status-use-history
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
;;   svn co http://svn.collab.net/repos/svn/trunk/contrib/client-side/psvn psvn

;; TODO:
;; * shortcut for svn propset svn:keywords "Date" psvn.el
;; * docstrings for the functions
;; * perhaps shortcuts for ranges, dates
;; * when editing the command line - offer help from the svn client
;; * finish svn-status-property-set
;; * Add repository browser
;; * Improve support for svn blame
;; * Get rid of all byte-compiler warnings
;; * SVK working copy support
;; * multiple independent buffers in svn-status-mode
;; There are "TODO" comments in other parts of this file as well.

;; Overview over the implemented/not (yet) implemented svn sub-commands:
;; * add                       implemented
;; * blame                     implemented
;; * cat                       implemented
;; * checkout (co)
;; * cleanup                   implemented
;; * commit (ci)               implemented
;; * copy (cp)
;; * delete (del, remove, rm)  implemented
;; * diff (di)                 implemented
;; * export                    implemented
;; * help (?, h)
;; * import
;; * info                      implemented
;; * list (ls)
;; * log                       implemented
;; * merge
;; * mkdir                     implemented
;; * move (mv, rename, ren)    implemented
;; * propdel (pdel)            implemented
;; * propedit (pedit, pe)      not needed
;; * propget (pget, pg)        used
;; * proplist (plist, pl)      implemented
;; * propset (pset, ps)        used
;; * resolved                  implemented
;; * revert                    implemented
;; * status (stat, st)         implemented
;; * switch (sw)
;; * update (up)               implemented

;; For the not yet implemented commands you should use the command line
;; svn client. If there are user requests for any missing commands I will
;; probably implement them.

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

(condition-case nil
    (progn
      (require 'diff-mode))
  (error nil))

;;; user setable variables
(defcustom svn-status-verbose t
  "*Add '-v' to svn status call."
  :type 'boolean
  :group 'psvn)
(defcustom svn-log-edit-file-name "++svn-log++"
  "*Name of a saved log file.
This can be either absolute, or relative to the default directory
of the *svn-log-edit* buffer."
  :type 'file
  :group 'psvn)
(put 'svn-log-edit-file-name 'risky-local-variable t)
(defcustom svn-log-edit-insert-files-to-commit t
  "*Insert the filelist to commit in the *svn-log* buffer"
  :type 'boolean
  :group 'psvn)
(defcustom svn-log-edit-use-log-edit-mode
  (and (condition-case nil (require 'log-edit) (error nil)) t)
  "*Use log-edit-mode as base for svn-log-edit-mode
This variable takes effect only when psvn.el is being loaded."
  :type 'boolean
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

Setting this variable to nil speeds up \[M-x svn-status], however the
listing may then become incorrect.

This can be toggled with \\[svn-status-toggle-sort-status-buffer]."
  :type 'boolean
  :group 'psvn)

(defcustom svn-status-unmark-files-after-list '(commit revert)
  "*List of operations after which all user marks will be removed.
Possible values are: commit, revert."
  :type '(set (const commit)
              (const revert))
  :group 'psvn)

(defcustom svn-status-preserve-window-configuration nil
  "*Try to preserve the window configuration."
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

(defcustom svn-status-svn-environment-var-list '()
  "*A list of environment variables that should be set for that svn process.
Each element is either a string \"VARIABLE=VALUE\" which will be added to
the environment when svn is run, or just \"VARIABLE\" which causes that
variable to be entirely removed from the environment.

You could set this for example to '(\"LANG=C\")"
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
nil       ... show in *svn-process* buffer
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

(defvar svn-status-buffer-name "*svn-status*" "Name for the svn status buffer")

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
(defcustom svn-status-default-log-arguments '()
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

(defcustom svn-status-default-diff-arguments '()
  "*A list of arguments that is passed to the svn diff command.
If you'd like to suppress whitespace changes use the following value:
'(\"--diff-cmd\" \"diff\" \"-x\" \"-wbBu\")"
  :type '(repeat string)
  :group 'psvn)
(put 'svn-status-default-diff-arguments 'risky-local-variable t)

(defvar svn-trac-project-root nil
  "Path for an eventual existing trac issue tracker.
This can be set with \\[svn-status-set-trac-project-root].")

(defvar svn-status-module-name nil
  "*A short name for the actual project.
This can be set with \\[svn-status-set-module-name].")

(defvar svn-status-load-state-before-svn-status t
  "*Whether to automatically restore state from ++psvn.state file before running svn-status.")

;;; hooks
(defvar svn-log-edit-mode-hook nil "Hook run when entering `svn-log-edit-mode'.")
(defvar svn-log-edit-done-hook nil "Hook run after commiting files via svn.")
;; (put 'svn-log-edit-mode-hook 'risky-local-variable t)
;; (put 'svn-log-edit-done-hook 'risky-local-variable t)
;; already implied by "-hook" suffix

(defvar svn-status-coding-system nil
  "A special coding system is needed for the output of svn.
svn-status-coding-system is used in svn-run, if it is not nil.")

(defcustom svn-status-wash-control-M-in-process-buffers
  (eq system-type 'windows-nt)
  "*Remove any trailing ^M from the *svn-process* buffer."
  :type 'boolean
  :group 'psvn)

;;; experimental features
(defvar svn-status-track-user-input nil "Track user/password queries.
This feature is implemented via a process filter.
It is an experimental feature.")

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

;; Use the normally used mode for files ending in .~HEAD~, .~BASE~, ...
(add-to-list 'auto-mode-alist '("\\.~?\\(HEAD\\|BASE\\|PREV\\)~?\\'" ignore t))

;;; internal variables
(defvar svn-status-directory-history nil "List of visited svn working directories.")
(defvar svn-process-cmd nil)
(defvar svn-status-info nil)
(defvar svn-status-filename-to-buffer-position-cache (make-hash-table :test 'equal :weakness t))
(defvar svn-status-base-info nil)
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
(defvar svn-status-propedit-property-name nil)
(defvar svn-status-propedit-file-list nil)
(defvar svn-status-mode-line-process "")
(defvar svn-status-mode-line-process-status "")
(defvar svn-status-mode-line-process-edit-flag "")
(defvar svn-status-edit-svn-command nil)
(defvar svn-status-update-previous-process-output nil)
(defvar svn-pre-run-asynch-recent-keys nil)
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
(defvar svn-status-operated-on-dot nil)
(defvar svn-status-elided-list nil)
(defvar svn-status-custom-hide-function nil)
;; (put 'svn-status-custom-hide-function 'risky-local-variable t)
;; already implied by "-function" suffix
(defvar svn-status-get-specific-revision-file-info)
(defvar svn-status-last-output-buffer-name)
(defvar svn-transient-buffers)
(defvar svn-ediff-windows)
(defvar svn-ediff-result)

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

; compatibility
; emacs 20
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


;;; keymaps

(defvar svn-global-keymap nil "Global keymap for psvn.el.
To bind this to a different key, customize `svn-status-prefix-key'.")
(put 'svn-global-keymap 'risky-local-variable t)
(when (not svn-global-keymap)
  (setq svn-global-keymap (make-sparse-keymap))
  (define-key svn-global-keymap (kbd "s") 'svn-status-this-directory)
  (define-key svn-global-keymap (kbd "l") 'svn-status-show-svn-log)
  (define-key svn-global-keymap (kbd "u") 'svn-status-update-cmd)
  (define-key svn-global-keymap (kbd "=") 'svn-status-show-svn-diff)
  (define-key svn-global-keymap (kbd "c") 'svn-status-commit)
  (define-key svn-global-keymap (kbd "b") 'svn-status-switch-to-status-buffer)
  (define-key svn-global-keymap (kbd "o") 'svn-status-pop-to-status-buffer))

(defvar svn-status-diff-mode-map ()
  "Keymap used in `svn-status-diff-mode' for additional commands that are not defined in diff-mode.")
(put 'svn-status-diff-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-status-diff-mode-map)
  (setq svn-status-diff-mode-map (copy-keymap diff-mode-shared-map))
  (define-key svn-status-diff-mode-map [?w] 'svn-status-diff-save-current-defun-as-kill))


(defvar svn-global-trac-map ()
  "Subkeymap used in `svn-global-keymap' for trac issue tracker commands.")
(put 'svn-global-trac-map 'risky-local-variable t) ;for Emacs 20.7
(when (not svn-global-trac-map)
  (setq svn-global-trac-map (make-sparse-keymap))
  (define-key svn-global-trac-map (kbd "t") 'svn-trac-browse-timeline)
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



;;;###autoload (defalias 'svn-examine 'svn-status)
(defalias 'svn-examine 'svn-status)

;;;###autoload
(defun svn-status (dir &optional arg)
  "Examine the status of Subversion working copy in directory DIR.
If ARG is -, allow editing of the parameters. One could add -N to
run svn status non recursively to make it faster.
For every other non nil ARG pass the -u argument to `svn status'.

If there is no .svn directory, examine if there is SVN and run
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
      (svn-status-load-state t)))
  (setq svn-status-directory-history (delete dir svn-status-directory-history))
  (add-to-list 'svn-status-directory-history dir)
  (if (string= (buffer-name) svn-status-buffer-name)
      (setq svn-status-display-new-status-buffer nil)
    (setq svn-status-display-new-status-buffer t)
    ;;(message "psvn: Saving initial window configuration")
    (setq svn-status-initial-window-configuration
          (current-window-configuration)))
  (let* ((status-buf (get-buffer-create svn-status-buffer-name))
         (proc-buf (get-buffer-create "*svn-process*"))
         (want-edit (eq arg '-))
         (status-option (if want-edit
                            (if svn-status-verbose "-v" "")
                          (if svn-status-verbose
                              (if arg "-uv" "-v")
                            (if arg "-u" ""))))
         (svn-status-edit-svn-command
          (or want-edit svn-status-edit-svn-command)))
    (save-excursion
      (set-buffer status-buf)
      (setq default-directory dir)
      (set-buffer proc-buf)
      (setq default-directory dir
            svn-status-remote (when arg t))
      (svn-run t t 'status "status" status-option))))

(defun svn-status-this-directory (arg)
  "Run `svn-status' for the `default-directory'"
  (interactive "P")
  (svn-status default-directory arg))

(defun svn-status-use-history ()
  (interactive)
  (let* ((hist svn-status-directory-history)
         (dir (read-from-minibuffer "svn-status on directory: "
                              (cadr svn-status-directory-history)
                              nil nil 'hist)))
    (if (file-directory-p dir)
        (svn-status dir)
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
*svn-process* buffer before commencing.

CMDTYPE is a symbol such as 'mv, 'revert, or 'add, representing the
command to run.

ARGLIST is a list of arguments \(which must include the command name,
for example: '(\"revert\" \"file1\"\)
ARGLIST is flattened and any every nil value is discarded.

If the variable `svn-status-edit-svn-command' is non-nil then the user
can edit ARGLIST before running svn."
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
        (let* ((proc-buf (get-buffer-create "*svn-process*"))
               (svn-exe svn-status-svn-executable)
               (svn-proc))
          (when (listp (car arglist))
            (setq arglist (car arglist)))
          (save-excursion
            (set-buffer proc-buf)
            (when svn-status-coding-system
              (setq buffer-file-coding-system svn-status-coding-system))
            (setq buffer-read-only nil)
            (fundamental-mode)
            (if clear-process-buffer
                (delete-region (point-min) (point-max))
              (goto-char (point-max)))
            (setq svn-process-cmd cmdtype)
            (setq svn-status-mode-line-process-status (format " running %s" cmdtype))
            (svn-status-update-mode-line)
            (sit-for 0.1)
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
                    (setq svn-proc (apply 'start-process "svn" proc-buf svn-exe arglist)))
                  (set-process-sentinel svn-proc 'svn-process-sentinel)
                  (when svn-status-track-user-input
                    (set-process-filter svn-proc 'svn-process-filter)))
              ;;(message "running synchron: %s %S" svn-exe arglist)
              (let ((process-environment (svn-process-environment)))
                ;; `call-process' ignores `process-connection-type' and
                ;; never opens a pseudoterminal.
                (apply 'call-process svn-exe nil proc-buf nil arglist))
              (setq svn-status-mode-line-process-status "")
              (svn-status-update-mode-line)))))
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
    (set-buffer (process-buffer process))
    (setq svn-status-mode-line-process-status "")
    (svn-status-update-mode-line)
    (cond ((string= event "finished\n")
           (cond ((eq svn-process-cmd 'status)
                  ;;(message "svn status finished")
                  (svn-process-sentinel-fixup-path-seperators)
                  (svn-parse-status-result)
                  (set-buffer act-buf)
                  (svn-status-update-buffer)
                  (when svn-status-update-previous-process-output
                    (set-buffer (process-buffer process))
                    (delete-region (point-min) (point-max))
                    (insert "Output from svn command:\n")
                    (insert svn-status-update-previous-process-output)
                    (goto-char (point-min))
                    (setq svn-status-update-previous-process-output nil))
                  (when svn-status-display-new-status-buffer
                    (set-window-configuration svn-status-initial-window-configuration)
                    (if (svn-had-user-input-since-asynch-run)
                        (message "svn status finished")
                      (switch-to-buffer svn-status-buffer-name))))
                 ((eq svn-process-cmd 'log)
                  (svn-status-show-process-output 'log t)
                  (pop-to-buffer svn-status-last-output-buffer-name)
                  (svn-log-view-mode)
                  (forward-line 3)
                  (font-lock-fontify-buffer)
                  (message "svn log finished"))
                 ((eq svn-process-cmd 'info)
                  (svn-status-show-process-output 'info t)
                  (message "svn info finished"))
                 ((eq svn-process-cmd 'parse-info)
                  (svn-status-parse-info-result))
                 ((eq svn-process-cmd 'blame)
                  (svn-status-show-process-output 'blame t)
                  (message "svn blame finished"))
                 ((eq svn-process-cmd 'commit)
                  (svn-process-sentinel-fixup-path-seperators)
                  (svn-status-remove-temp-file-maybe)
                  (when (member 'commit svn-status-unmark-files-after-list)
                    (svn-status-unset-all-usermarks))
                  (svn-status-update-with-command-list (svn-status-parse-commit-output))
                  (run-hooks 'svn-log-edit-done-hook)
                  (setq svn-status-files-to-commit nil
                        svn-status-recursive-commit nil)
                  (message "svn commit finished"))
                 ((eq svn-process-cmd 'update)
                  (svn-status-show-process-output 'update t)
                  (svn-status-update)
                  (message "svn update finished"))
                 ((eq svn-process-cmd 'add)
                  (svn-status-update-with-command-list (svn-status-parse-ar-output))
                  (message "svn add finished"))
                 ((eq svn-process-cmd 'mkdir)
                  (svn-status-update)
                  (message "svn mkdir finished"))
                 ((eq svn-process-cmd 'revert)
                  (when (member 'revert svn-status-unmark-files-after-list)
                    (svn-status-unset-all-usermarks))
                  (svn-status-update)
                  (message "svn revert finished"))
                 ((eq svn-process-cmd 'resolved)
                  (svn-status-update)
                  (message "svn resolved finished"))
                 ((eq svn-process-cmd 'mv)
                  (svn-status-update)
                  (message "svn mv finished"))
                 ((eq svn-process-cmd 'rm)
                  (svn-status-update-with-command-list (svn-status-parse-ar-output))
                  (message "svn rm finished"))
                 ((eq svn-process-cmd 'cleanup)
                  (message "svn cleanup finished"))
                 ((eq svn-process-cmd 'proplist)
                  (svn-status-show-process-output 'proplist t)
                  (message "svn proplist finished"))
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
           (message "svn failed: %s"
                    (if (re-search-backward "^svn: \\(.*\\)" nil t)
                        (match-string 1)
                      event)))
          (t
           (message "svn process had unknown event: %s" event))
          (svn-status-show-process-output nil t))))

(defun svn-process-filter (process str)
  (save-window-excursion
    (set-buffer "*svn-process*")
    ;;(message "svn-process-filter: %s" str)
    (goto-char (point-max))
    (insert str)
    (save-excursion
      (goto-char (svn-point-at-bol))
      (when (looking-at "Password for '\\(.+\\)': ")
        ;(svn-status-show-process-buffer)
        (let ((passwd (read-passwd
                       (format "Enter svn password for %s: " (match-string 1)))))
          (svn-process-send-string (concat passwd "\n") t)))
      (when (looking-at "Username: ")
        (let ((user-name (read-string "Username for svn operation: ")))
          (svn-process-send-string (concat user-name "\n")))))))

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
  (append (mapcar (lambda (dir)
                    (list (or (gethash dir old-ui-information)
                              (svn-status-make-ui-status))
                          32 nil dir -1 -1 "?" nil nil nil nil))
                  dir-list)
          svn-status-info))


(defun svn-parse-status-result ()
  "Parse the *svn-process* buffer.
The results are used to build the `svn-status-info' variable."
  (setq svn-status-head-revision nil)
  (save-excursion
    (let ((old-ui-information (svn-status-ui-information-hash-table))
          (svn-marks)
          (svn-file-mark)
          (svn-property-mark)
          (svn-locked-mark)
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
          (svn-marks-length (if (and svn-status-verbose svn-status-remote)
                                8 5))
          (dir-set '(".")))
      (set-buffer "*svn-process*")
      (setq svn-status-info nil)
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
          (forward-line)
          )
         (t
          (setq svn-marks (buffer-substring (point) (+ (point) svn-marks-length))
                svn-file-mark (elt svn-marks 0)         ; 1st column - M,A,C,D,G,? etc
                svn-property-mark (elt svn-marks 1)     ; 2nd column - M,C (properties)
                svn-locked-mark (elt svn-marks 2)       ; 3rd column - L or blank
                svn-with-history-mark (elt svn-marks 3) ; 4th column - + or blank
                svn-switched-mark (elt svn-marks 4))     ; 5th column - S or blank
          (if (and svn-status-verbose svn-status-remote)
              (setq svn-update-mark (elt svn-marks 7))) ; 8th column - * or blank
          (when (eq svn-property-mark ?\ )     (setq svn-property-mark nil))
          (when (eq svn-locked-mark ?\ )       (setq svn-locked-mark nil))
          (when (eq svn-with-history-mark ?\ ) (setq svn-with-history-mark nil))
          (when (eq svn-switched-mark ?\ )     (setq svn-switched-mark nil))
          (when (eq svn-update-mark ?\ )       (setq svn-update-mark nil))
          (forward-char svn-marks-length)
          (skip-chars-forward " ")
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
                  author (if (eq svn-file-mark 88) "" "?"))) ;clear author of svn:externals dirs
           (t
            (error "Unknown status line format")))
          (unless path (setq path "."))
          (setq dir (file-name-directory path))
          (if (and (not svn-status-verbose) dir)
              (let ((dirname (directory-file-name dir)))
                (if (not (member dirname dir-set))
                    (setq dir-set (cons dirname dir-set)))))
          (setq svn-status-info (cons (list (or (gethash path old-ui-information)
                                                (svn-status-make-ui-status))
                                            svn-file-mark
                                            svn-property-mark
                                            path
                                            local-rev
                                            last-change-rev
                                            author
                                            svn-update-mark
                                            svn-locked-mark
                                            svn-with-history-mark
                                            svn-switched-mark)
                                      svn-status-info))
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

(when (not svn-status-mode-map)
  (setq svn-status-mode-map (make-sparse-keymap))
  (suppress-keymap svn-status-mode-map)
  ;; Don't use (kbd "<return>"); it's unreachable with GNU Emacs 21.3 on a TTY.
  (define-key svn-status-mode-map (kbd "RET") 'svn-status-find-file-or-examine-directory)
  (define-key svn-status-mode-map (kbd "<mouse-2>") 'svn-status-mouse-find-file-or-examine-directory)
  (define-key svn-status-mode-map (kbd "^") 'svn-status-examine-parent)
  (define-key svn-status-mode-map (kbd "s") 'svn-status-show-process-buffer)
  (define-key svn-status-mode-map (kbd "f") 'svn-status-find-files)
  (define-key svn-status-mode-map (kbd "o") 'svn-status-find-file-other-window)
  (define-key svn-status-mode-map (kbd "v") 'svn-status-view-file-other-window)
  (define-key svn-status-mode-map (kbd "e") 'svn-status-toggle-edit-cmd-flag)
  (define-key svn-status-mode-map (kbd "g") 'svn-status-update)
  (define-key svn-status-mode-map (kbd "M-s") 'svn-status-update) ;; PCL-CVS compatibility
  (define-key svn-status-mode-map (kbd "q") 'svn-status-bury-buffer)
  (define-key svn-status-mode-map (kbd "h") 'svn-status-use-history)
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
  (define-key svn-status-mode-map (kbd "w") 'svn-status-copy-filename-as-kill)
  (define-key svn-status-mode-map (kbd ".") 'svn-status-goto-root-or-return)
  (define-key svn-status-mode-map (kbd "I") 'svn-status-parse-info)
  (define-key svn-status-mode-map (kbd "V") 'svn-status-svnversion)
  (define-key svn-status-mode-map (kbd "?") 'svn-status-toggle-hide-unknown)
  (define-key svn-status-mode-map (kbd "_") 'svn-status-toggle-hide-unmodified)
  (define-key svn-status-mode-map (kbd "a") 'svn-status-add-file)
  (define-key svn-status-mode-map (kbd "A") 'svn-status-add-file-recursively)
  (define-key svn-status-mode-map (kbd "+") 'svn-status-make-directory)
  (define-key svn-status-mode-map (kbd "R") 'svn-status-mv)
  (define-key svn-status-mode-map (kbd "D") 'svn-status-rm)
  (define-key svn-status-mode-map (kbd "c") 'svn-status-commit)
  (define-key svn-status-mode-map (kbd "M-c") 'svn-status-cleanup)
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

  (define-key svn-status-mode-map (kbd "C-n") 'svn-status-next-line)
  (define-key svn-status-mode-map (kbd "C-p") 'svn-status-previous-line)
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
  (define-key svn-status-mode-mark-map (kbd "D") 'svn-status-mark-deleted)
  (define-key svn-status-mode-mark-map (kbd "*") 'svn-status-mark-changed)
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
  (define-key svn-status-mode-property-map (kbd "y") 'svn-status-property-set-eol-style)
  (define-key svn-status-mode-property-map (kbd "x") 'svn-status-property-set-executable)
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
  (define-key svn-status-mode-options-map (kbd "f") 'svn-status-toggle-display-full-path)
  (define-key svn-status-mode-options-map (kbd "t") 'svn-status-set-trac-project-root)
  (define-key svn-status-mode-options-map (kbd "n") 'svn-status-set-module-name)
  (define-key svn-status-mode-map (kbd "O") svn-status-mode-options-map))
(when (not svn-status-mode-trac-map)
  (setq svn-status-mode-trac-map (make-sparse-keymap))
  (define-key svn-status-mode-trac-map (kbd "t") 'svn-trac-browse-timeline)
  (define-key svn-status-mode-map (kbd "T") svn-status-mode-trac-map))

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
    ["svn cat ..." svn-status-get-specific-revision t]
    ["svn add" svn-status-add-file t]
    ["svn add recursively" svn-status-add-file-recursively t]
    ["svn mkdir..." svn-status-make-directory t]
    ["svn mv..." svn-status-mv t]
    ["svn rm..." svn-status-rm t]
    ["svn export..." svn-status-export t]
    ["Up Directory" svn-status-examine-parent t]
    ["Elide Directory" svn-status-toggle-elide t]
    ["svn revert" svn-status-revert t]
    ["svn resolved" svn-status-resolved t]
    ["svn cleanup" svn-status-cleanup t]
    ["Show Process Buffer" svn-status-show-process-buffer t]
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
     ["Select svn:eol-style" svn-status-property-set-eol-style t]
     ["Set svn:executable" svn-status-property-set-executable t]
     )
    ("Options"
     ["Save Options" svn-status-save-state t]
     ["Load Options" svn-status-load-state t]
     ["Set Trac project root" svn-status-set-trac-project-root t]
     ["Set Short module name" svn-status-set-module-name t]
     ["Toggle sorting of *svn-status* buffer" svn-status-toggle-sort-status-buffer
      :style toggle :selected svn-status-sort-status-buffer]
     ["Toggle display of full path names" svn-status-toggle-display-full-path
      :style toggle :selected svn-status-display-full-path]
     )
    ("Trac"
     ["Browse timeline" svn-trac-browse-timeline t]
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
     ["Mark/Unmark added" svn-status-mark-added t]
     ["Mark/Unmark modified" svn-status-mark-modified t]
     ["Mark/Unmark deleted" svn-status-mark-deleted t]
     ["Mark/Unmark modified/added/deleted" svn-status-mark-changed t]
     )
    ["Hide Unknown" svn-status-toggle-hide-unknown
     :style toggle :selected svn-status-hide-unknown]
    ["Hide Unmodified" svn-status-toggle-hide-unmodified
     :style toggle :selected svn-status-hide-unmodified]
    ))


(defun svn-status-popup-menu (event)
  (interactive "e")
  (mouse-set-point event)
  (let* ((line-info (svn-status-get-line-information))
         (name (svn-status-line-info->filename line-info)))
    (when line-info
      (easy-menu-define svn-status-actual-popup-menu nil nil
        (list name
               ["svn diff" svn-status-show-svn-diff t]
               ["svn commit" svn-status-commit t]
               ["svn log" svn-status-show-svn-log t]
               ["svn info" svn-status-info t]
               ["svn blame" svn-status-blame t]))
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
  *svn-log-edit*
  *svn-property-edit*
  *svn-log*
  *svn-process*
When called with a prefix argument, ARG, switch back to the window configuration that was
in use before `svn-status' was called."
  (interactive "P")
  (cond (arg
         (when svn-status-initial-window-configuration
           (set-window-configuration svn-status-initial-window-configuration)))
        (t
         (let ((bl '("*svn-log-edit*" "*svn-property-edit*" "*svn-log*" "*svn-process*")))
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
  (let ((ok t)
        (tree (or (svn-status-base-dir)
                  tree)))
    (unless tree
      (error "Not in a svn project tree"))
    (dolist (buffer (buffer-list))
      (with-current-buffer buffer
        (when (buffer-modified-p)
          (let ((file (buffer-file-name)))
            (when file
              (let ((root (svn-status-base-dir (file-name-directory file))))
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
(defun svn-status-line-info->author (line-info) (nth 6 line-info))
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

(defun svn-status-line-info->is-visiblep (line-info)
  (not (or (svn-status-line-info->hide-because-unknown line-info)
           (svn-status-line-info->hide-because-unmodified line-info)
           (svn-status-line-info->hide-because-user-elide line-info))))

(defun svn-status-line-info->hide-because-unknown (line-info)
  (and svn-status-hide-unknown
       (eq (svn-status-line-info->filemark line-info) ??)))

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

(defun svn-status-line-info->set-lastchangerev (line-info value)
  (setcar (nthcdr 5 line-info) value))

(defun svn-status-copy-filename-as-kill (arg)
  "Copy the actual file name to the kill-ring.
When called with the prefix argument 0, use the full path name."
  (interactive "P")
  (let ((str (if (eq arg 0)
                 (svn-status-line-info->full-path (svn-status-get-line-information))
               (svn-status-line-info->filename (svn-status-get-line-information)))))
    (kill-new str)
    (message "Copied %s" str)))

(defun svn-status-toggle-elide ()
  (interactive)
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
  (svn-status-update-buffer))

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
          (message "continue to search for %s" (caar cmd-list))
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
          (message "did not find %s" (caar cmd-list)))
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
    (cond ((equal action 'committed)
           (setq tag-string " <committed>"))
          ((equal action 'added)
           (setq tag-string " <added>"))
          ((equal action 'deleted)
           (setq tag-string " <deleted>"))
          ((equal action 'replaced)
           (setq tag-string " <replaced>"))
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
    (when tag-string
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
    (set-buffer "*svn-process*")
    (let ((action)
          (name)
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
          (setq name (buffer-substring-no-properties (point) (svn-point-at-eol)))
          (setq result (cons (list name action)
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
    (set-buffer "*svn-process*")
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

(defun svn-status-parse-property-output ()
  "Parse the output of svn propset.
Return a list that is suitable for `svn-status-update-with-command-list'"
  (save-excursion
    (set-buffer "*svn-process*")
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
                      (svn-status-choose-face-to-add
                       (svn-status-line-info->directory-p line-info)
                       (svn-status-line-info->filename-nondirectory line-info)
                       'svn-status-directory-face
                       'svn-status-filename-face)
                      ;; if it's a symlkink, add '-> target'
                      (let ((target (svn-status-line-info->symlink-p line-info)))
                        (when target
                          (concat " -> "
                                  ;; add face to target: could maybe
                                  ;; use different faces for
                                  ;; unversioned targets?
                                  (svn-status-choose-face-to-add
                                   (file-directory-p target)
                                   (file-relative-name
                                    target
                                    (svn-status-line-info->directory-containing-line-info
                                     line-info t)); name relative to dir of line-info, not '.'
                                   'svn-status-directory-face
                                   'svn-status-filename-face)
                                  )))
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
                     (if svn-status-short-mod-flag-p update-available filename)
                     (if svn-status-short-mod-flag-p filename update-available)
                     (svn-status-maybe-add-string (svn-status-line-info->locked line-info)
                                                  " [ LOCKED ]" 'svn-status-locked-face)
                     (svn-status-maybe-add-string (svn-status-line-info->switched line-info)
                                                  " (switched)" 'svn-status-switched-face)
                     elide-hint)
             'svn-status-marked-face)
            "\n")))

(defun svn-status-update-buffer ()
  "Update the `svn-status-buffer-name' buffer, using `svn-status-info'."
  (interactive)
  ;(message "buffer-name: %s" (buffer-name))
  (unless (string= (buffer-name) svn-status-buffer-name)
    (set-buffer svn-status-buffer-name))
  (svn-status-mode)
  (let ((st-info svn-status-info)
        (buffer-read-only nil)
        (start-pos)
        (overlay)
        (unmodified-count 0)    ;how many unmodified files are hidden
        (unknown-count 0)       ;how many unknown files are hidden
        (custom-hide-count 0)   ;how many files are hidden via svn-status-custom-hide-function
        (marked-count 0)        ;how many files are elided
        (user-elide-count 0)
        (fname (svn-status-line-info->filename (svn-status-get-line-information)))
        (fname-pos (point))
        (header-line-string)
        (column (current-column)))
    (delete-region (point-min) (point-max))
    (insert "\n")
    ;; Insert all files and directories
    (while st-info
      (setq start-pos (point))
      (cond ((svn-status-line-info->has-usermark (car st-info))
             ;; Show a marked file always
             (svn-insert-line-in-status-buffer (car st-info)))
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
    (when svn-status-base-info
      (insert (concat "Repository: " (svn-status-base-info->url) "\n")))
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
          (goto-char (+ column (svn-point-at-bol))))
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
    (svn-run nil t 'parse-info "info" ".")
    (svn-status-parse-info-result))
  (unless (eq arg t)
    (svn-status-update-buffer)))

(defun svn-status-parse-info-result ()
  (let ((url))
    (save-excursion
      (set-buffer "*svn-process*")
      (goto-char (point-min))
      (let ((case-fold-search t))
        (search-forward "url: "))
      (setq url (buffer-substring-no-properties (point) (svn-point-at-eol))))
    (setq svn-status-base-info `((url ,url)))))

(defun svn-status-base-info->url ()
  (if svn-status-base-info
      (cadr (assoc 'url svn-status-base-info))
    ""))

(defun svn-status-toggle-edit-cmd-flag (&optional reset)
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
  (interactive "p")
  (next-line nr-of-lines)
  (when (svn-status-get-line-information)
    (goto-char (+ (svn-point-at-bol) svn-status-default-column))))

(defun svn-status-previous-line (nr-of-lines)
  (interactive "p")
  (previous-line nr-of-lines)
  (when (svn-status-get-line-information)
    (goto-char (+ (svn-point-at-bol) svn-status-default-column))))

(defun svn-status-dired-jump ()
  "Jump to a dired buffer, containing the file at point."
  (interactive)
  (let* ((line-info (svn-status-get-line-information))
         (file-full-path (svn-status-line-info->full-path line-info)))
    (let ((default-directory
            (file-name-as-directory
             (expand-file-name (svn-status-line-info->directory-containing-line-info line-info t)))))
      (dired-jump))
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
      (set-buffer "*svn-process*")
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
    '((nil nil) 32 nil "." 0 0 "" nil nil nil nil)))


(defun svn-status-get-file-list (use-marked-files)
  "Get either the selected files or the file under point.
USE-MARKED-FILES decides which we do.
See `svn-status-marked-files' for what counts as selected."
  (if use-marked-files
      (svn-status-marked-files)
    (list (svn-status-get-line-information))))

(defun svn-status-get-file-list-names (use-marked-files)
  (mapcar 'svn-status-line-info->filename (svn-status-get-file-list use-marked-files)))

(defun svn-status-select-line ()
    "Return information about the file under point.
\(Only used for debugging\)"
  (interactive)
  (let ((info (svn-status-get-line-information)))
    (if info
        (message "%S %S %S" info (svn-status-line-info->hide-because-unknown info)
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
                       '(nil nil nil ""))))
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
         (sub-file-regexp (concat "^" (regexp-quote
                                       (file-name-as-directory file-name))))
         (newcursorpos-fname)
         (i-fname)
         (current-line svn-start-of-file-list-line-number))
    (while st-info
      (when (svn-status-line-info->is-visiblep (car st-info))
        (setq current-line (1+ current-line)))
      (setq i-fname (svn-status-line-info->filename (car st-info)))
      (when (or (string= file-name i-fname)
                (string-match sub-file-regexp i-fname))
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
If the function is called with a prefix ARG, unmark all these files."
  (interactive "P")
  (svn-status-apply-usermark-checked
   '(lambda (info) (or (eq (svn-status-line-info->filemark info) ?M)
                       (eq (svn-status-line-info->filemark info)
                           svn-status-file-modified-after-save-flag)))
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
  (let* ((st-info svn-status-info)
         (file-list))
    (while st-info
      (when (svn-status-line-info->has-usermark (car st-info))
        (setq file-list (append file-list (list (car st-info)))))
      (setq st-info (cdr st-info)))
    (or file-list
        (if (svn-status-get-line-information)
            (list (svn-status-get-line-information))
          nil))))

(defun svn-status-marked-file-names ()
  (mapcar 'svn-status-line-info->filename (svn-status-marked-files)))

(defun svn-status-some-files-marked-p ()
  "Return non-nil iff a file has been marked by `svn-status-set-user-mark'.
Unlike `svn-status-marked-files', this does not select the file under point
if no files have been marked."
  ;; `some' would be shorter but requires cl-seq at runtime.
  ;; (Because it accepts both lists and vectors, it is difficult to inline.)
  (loop for file in svn-status-info
        thereis (svn-status-line-info->has-usermark file)))

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
  (when (string= (buffer-name) svn-status-buffer-name)
    (delete-other-windows))
  (pop-to-buffer "*svn-process*")
  (svn-process-mode)
  (when svn-status-wash-control-M-in-process-buffers
    (svn-status-remove-control-M))
  (when scroll-to-top
    (goto-char (point-min)))
  (other-window 1))

(defun svn-status-show-process-output (cmd &optional scroll-to-top)
  "Display the result of a svn command.
Consider svn-status-window-alist to choose the buffer name."
  (let ((window-mode (cadr (assoc cmd svn-status-window-alist))))
    (cond ((eq window-mode nil) ;; use *svn-process* buffer
           (setq svn-status-last-output-buffer-name "*svn-process*"))
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
            (pop-to-buffer "*svn-process*")
            (switch-to-buffer (get-buffer-create svn-status-last-output-buffer-name))
            (let ((buffer-read-only nil))
              (delete-region (point-min) (point-max))
              (insert-buffer-substring "*svn-process*")
              (when scroll-to-top
                (goto-char (point-min))))
            (when (eq window-mode t) ;; *svn-info* buffer
              (svn-info-mode))
            (other-window 1))
        (svn-status-show-process-buffer-internal scroll-to-top)))))

(defun svn-status-show-svn-log (arg)
  "Run `svn log' on selected files.
The output is put into the *svn-log* buffer
The optional prefix argument ARG determines which switches are passed to `svn log':
 no prefix               --- use whatever is in the list `svn-status-default-log-arguments'
 prefix argument of -1   --- use no arguments
 prefix argument of 0:   --- use the -q switch (quiet)
 other prefix arguments: --- use the -v switch (verbose)

See `svn-status-marked-files' for what counts as selected."
  (interactive "P")
  (let ((switches (cond ((eq arg 0)  '("-q"))
                        ((eq arg -1) '())
                        (arg         '("-v"))
                        (t           svn-status-default-log-arguments))))
    (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-marked-files) "")
    (svn-run t t 'log "log" "--targets" svn-status-temp-arg-file switches)
    (save-excursion
      (set-buffer "*svn-process*")
      (svn-log-view-mode))))

(defun svn-status-info ()
  "Run `svn info' on all selected files.
See `svn-status-marked-files' for what counts as selected."
  (interactive)
  (svn-status-create-arg-file svn-status-temp-arg-file "" (svn-status-marked-files) "")
  (svn-run t t 'info "info" "--targets" svn-status-temp-arg-file))

(defun svn-status-blame (revision)
  "Run `svn blame' on the current file.
When called with a prefix argument, ask the user for the REVISION to use."
  (interactive "P")
  (when current-prefix-arg
    (setq revision (svn-status-read-revision-string "Blame for version: " "BASE")))
  (unless revision (setq revision "BASE"))
  (svn-run t t 'blame "blame" "-r" revision (svn-status-line-info->filename (svn-status-get-line-information))))

(defun svn-status-show-svn-diff (arg)
  "Run `svn diff' on the current file.
If the current file is a directory, compare it recursively.
If there is a newer revision in the repository, the diff is done against HEAD,
otherwise compare the working copy with BASE.
If ARG then prompt for revision to diff against."
  (interactive "P")
  (svn-status-ensure-cursor-on-file)
  (svn-status-show-svn-diff-internal (list (svn-status-get-line-information)) t
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
        ;; "*svn-status*" buffer, not that of the "*svn-process*" buffer.
        (let ((directory-p (svn-status-line-info->directory-p line-info)))
          (with-current-buffer "*svn-process*"
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


(defun svn-status-activate-diff-mode ()
  "Show the *svn-process* buffer, using the diff-mode."
  (svn-status-show-process-output 'diff t)
  (save-excursion
    (set-buffer svn-status-last-output-buffer-name)
    (svn-status-diff-mode)
    (setq buffer-read-only t)))


(define-derived-mode svn-status-diff-mode fundamental-mode "svn-diff"
  "Major mode to display svn diffs. Derives from `diff-mode'.

Commands:
\\{svn-status-diff-mode-map}
"
  (let ((diff-mode-shared-map (copy-keymap svn-status-diff-mode-map))
        major-mode mode-name)
    (diff-mode)))

(defun svn-status-show-process-buffer ()
  "Show the content of the *svn-process* buffer"
  (interactive)
  (svn-status-show-process-output nil))

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

(defun svn-status-make-directory (dir)
  "Run `svn mkdir DIR'."
  ;; TODO: Allow entering a URI interactively.
  ;; Currently, `read-file-name' corrupts it.
  (interactive (list (read-file-name "Make directory: "
                                     (svn-status-directory-containing-point t))))
  (unless (string-match "^[^:/]+://" dir) ; Is it a URI?
    (setq dir (file-relative-name dir)))
  (svn-run t t 'mkdir "mkdir" "--" dir))

;;TODO: write a svn-status-cp similar to this---maybe a common
;;function to do both?
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
  (let* ((marked-files (svn-status-marked-files))
         (num-of-files (length marked-files))
         dest)
    (if (= 1 num-of-files)
        ;; one file to rename, prompt for new name, or directory to move the
        ;; file into.
        (setq dest (read-file-name (format "Rename %s to: "
                                           (svn-status-line-info->filename (car marked-files)))
                                   (svn-status-directory-containing-point t)
                                   (svn-status-line-info->full-path (car marked-files))))
      ;;multiple files selected, so prompt for existing directory to mv them into.
      (setq dest (svn-read-directory-name (format "Move %d files to directory: " num-of-files)
                                          (svn-status-directory-containing-point t) nil t))
      (unless (file-directory-p dest)
        (error "%s is not a directory" dest)))
    (when (string= dest "")
      (error "No destination entered; no files moved"))
    (unless (string-match "^[^:/]+://" dest) ; Is it a URI?
      (setq dest (file-relative-name dest)))
;
    ;;do the move: svn mv only lets us move things once at a time, so
    ;;we need to run svn mv once for each file (hence second arg to
    ;;svn-run is nil.)

    ;;TODO: before doing any moving, For every marked directory,
    ;;ensure none of its contents are also marked, since we dont want
    ;;to move both file *and* its parent...
    ;; what about hidden files?? what if user marks a dir+contents, then presses `_' ??
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
            (original-propmarks (svn-status-line-info->propmark original)))
        (cond
         ((or (eq original-filemarks 77)  ;;original has local mods: maybe do `svn mv --force'
              (eq original-propmarks 77)) ;;original has local prop mods: maybe do `svn mv --force'
          (if (yes-or-no-p (format "%s has local modifications; use `--force' to really move it? "
                                   original-name))
              (svn-run nil t 'mv "mv" "--force" "--" original-name dest)
            (message "Not moving %s" original-name)))
         ((eq original-filemarks 63) ;;original is unversioned: maybe do plain `mv'
          (if (yes-or-no-p (format "%s is unversioned.  Use plain `mv -i %s %s'? "
                                   original-name original-name dest))
              (call-process "mv" nil (get-buffer-create "*svn-process*") nil "-i" original-name dest)
            (message "Not moving %s" original-name)))

         ((eq original-filemarks 65) ;;original has `A' mark (eg it was `svn add'ed, but not committed)
          (message "Not moving %s (try committing it first)" original-name))

         ((eq original-filemarks 32) ;;original is unmodified: can use `svn mv'
          (svn-run nil t 'mv "mv" "--" original-name dest))

         ;;file is conflicted in some way?
         (t
          (if (yes-or-no-p (format "The status of %s looks scary.  Risk moving it anyway? " original-name))
              (svn-run nil t 'mv "mv" "--" original-name dest)
            (message "Not moving %s" original-name))))))
        (svn-status-update)))

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
When called with a prefix argument add the command line switch --force."
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
          (svn-run t t 'rm "rm" "--force" "--targets" svn-status-temp-arg-file)
        (svn-run t t 'rm "rm" "--targets" svn-status-temp-arg-file)))))

(defun svn-status-update-cmd ()
  "Run svn update."
  (interactive)
  (message "Running svn-update for %s" default-directory)
  ;TODO: use file names also
  (svn-run t t 'update "update"))

(defun svn-status-commit ()
  "Commit selected files.
If some files have been marked, commit those non-recursively;
this is because marking a directory with \\[svn-status-set-user-mark]
normally marks all of its files as well.
If no files have been marked, commit recursively the file at point."
  (interactive)
  (svn-status-save-some-buffers)
  (let* ((selected-files (svn-status-marked-files))
         (marked-files-p (svn-status-some-files-marked-p)))
    (setq svn-status-files-to-commit selected-files
          svn-status-recursive-commit (not marked-files-p))
    (svn-log-edit-show-files-to-commit)
    (svn-status-pop-to-commit-buffer)
    (when svn-log-edit-insert-files-to-commit
      (svn-log-edit-insert-files-to-commit))))

(defun svn-status-pop-to-commit-buffer ()
  (interactive)
  (setq svn-status-pre-commit-window-configuration (current-window-configuration))
  (let* ((use-existing-buffer (get-buffer "*svn-log-edit*"))
         (commit-buffer (get-buffer-create "*svn-log-edit*"))
         (dir default-directory))
    (pop-to-buffer commit-buffer)
    (setq default-directory dir)
    (unless use-existing-buffer
      (when (and svn-log-edit-file-name (file-readable-p svn-log-edit-file-name))
        (insert-file-contents svn-log-edit-file-name)))
    (svn-log-edit-mode)))

(defun svn-status-switch-to-status-buffer ()
  "Switch to the `svn-status-buffer-name' buffer."
  (interactive)
  (switch-to-buffer svn-status-buffer-name))

(defun svn-status-pop-to-status-buffer ()
  "Pop to the `svn-status-buffer-name' buffer."
  (interactive)
  (pop-to-buffer svn-status-buffer-name))

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
                    (message "psvn: file %s not found, updating %s buffer content..."
                             i-fname svn-status-buffer-name)
                    (svn-status-update-buffer))))))
          (setq st-info (cdr st-info))))))
  nil)

(add-hook 'after-save-hook 'svn-status-after-save-hook)

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
   (svn-status-get-file-list (not arg))
   :ask))

(defun svn-status-get-specific-revision-internal (line-infos revision)
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
  ;;
  ;; TODO: Return the alist, instead of storing it in a variable.

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

  (setq svn-status-get-specific-revision-file-info '())
  (dolist (line-info line-infos)
    (let* ((revision (if (eq revision :auto)
                         (if (svn-status-line-info->update-available line-info)
                             "HEAD" "BASE")
                       revision))       ;must be a string by this point
           (file-name (svn-status-line-info->filename line-info))
           ;; If REVISION is e.g. "HEAD", should we find out the actual
           ;; revision number and save "foo.~123~" rather than "foo.~HEAD~"?
           ;; OTOH, `auto-mode-alist' already ignores ".~HEAD~" suffixes,
           ;; and if users often want to know the revision numbers of such
           ;; files, they can use svn:keywords.
           (file-name-with-revision (concat file-name ".~" revision "~")))
      ;; `add-to-list' would unnecessarily check for duplicates.
      (push (cons file-name file-name-with-revision)
            svn-status-get-specific-revision-file-info)
      (save-excursion
        (let ((content
               (with-temp-buffer
                 (if (string= revision "BASE")
                     (insert-file-contents (concat (file-name-directory file-name)
                                                   (svn-wc-adm-dir-name)
                                                   "/text-base/"
                                                   (file-name-nondirectory file-name)
                                                   ".svn-base"))
                   (progn
                     (svn-run nil t 'cat "cat" "-r" revision file-name)
                     ;;todo: error processing
                     ;;svn: Filesystem has no item
                     ;;svn: file not found: revision `15', path `/trunk/file.txt'
                     (insert-buffer-substring "*svn-process*")))
                 (buffer-string))))
          (find-file file-name-with-revision)
          (setq buffer-read-only nil)
          (erase-buffer)  ;Widen, because we'll save the whole buffer.
          (insert content)
          (save-buffer)))))
  (setq svn-status-get-specific-revision-file-info
        (nreverse svn-status-get-specific-revision-file-info))
  (message "svn-status-get-specific-revision-file-info: %S"
           svn-status-get-specific-revision-file-info))


(defun svn-status-ediff-with-revision (arg)
  "Run ediff on the current file with a previous revision.
If ARG then prompt for revision to diff against."
  (interactive "P")
  (svn-status-get-specific-revision-internal
   (list (svn-status-get-line-information))
   (if arg :ask :auto))
  (let* ((ediff-after-quit-destination-buffer (current-buffer))
         (my-buffer (find-file-noselect (caar svn-status-get-specific-revision-file-info)))
         (base-buff (find-file-noselect (cdar svn-status-get-specific-revision-file-info)))
         (svn-transient-buffers (list base-buff ))
         (startup-hook '(svn-ediff-startup-hook)))
    (ediff-buffers base-buff my-buffer startup-hook)))

(defun svn-ediff-startup-hook ()
  (add-hook 'ediff-after-quit-hook-internal
        `(lambda ()
           (svn-ediff-exit-hook
        ',ediff-after-quit-destination-buffer ',svn-transient-buffers))
        nil 'local))

(defun svn-ediff-exit-hook (svn-buf tmp-bufs)
  ;; kill the temp buffers (and their associated windows)
  (dolist (tb tmp-bufs)
    (when (and tb (buffer-live-p tb) (not (buffer-modified-p tb)))
      (let ((win (get-buffer-window tb t)))
    (when win (delete-window win))
    (kill-buffer tb))))
  ;; switch back to the *svn* buffer
  (when (and svn-buf (buffer-live-p svn-buf)
         (not (get-buffer-window svn-buf t)))
    (ignore-errors (switch-to-buffer svn-buf))))


(defun svn-status-read-revision-string (prompt &optional default-value)
  "Prompt the user for a svn revision number."
  (interactive)
  (read-string prompt default-value))

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
    (set-buffer "*svn-process*")
    (goto-char (point-max))
    (let ((buffer-read-only nil))
      (insert (if send-passwd (make-string (length string) ?.) string)))
    (set-marker (process-mark (get-process "svn")) (point)))
  (process-send-string "svn" string))

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
      (set-buffer "*svn-process*")
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

(defun svn-status-property-edit (file-info-list prop-name &optional new-prop-value)
  (let* ((commit-buffer (get-buffer-create "*svn-property-edit*"))
         (dir default-directory)
         ;; now only one file is implemented ...
         (file-name (svn-status-line-info->filename (car file-info-list)))
         (prop-value))
    (message "Edit property %s for file %s" prop-name file-name)
    (svn-run nil t 'propget-parse "propget" prop-name file-name)
    (save-excursion
      (set-buffer "*svn-process*")
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
        (message "Adding new prop values %S " new-prop-value)
        (while new-prop-value
          (goto-char (point-min))
          (unless (re-search-forward
                   (concat "^" (regexp-quote (car new-prop-value)) "$") nil t)
            (goto-char (point-max))
            (when (> (current-column) 0) (insert "\n"))
            (insert (car new-prop-value)))
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
  (message "svn propset %s on %s"
           svn-status-propedit-property-name
           (mapcar 'svn-status-line-info->filename svn-status-propedit-file-list))
  (save-excursion
    (set-buffer (get-buffer "*svn-property-edit*"))
    (when (fboundp 'set-buffer-file-coding-system)
      (set-buffer-file-coding-system 'undecided-unix nil))
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

(if svn-log-edit-use-log-edit-mode
    (define-derived-mode svn-log-edit-mode log-edit-mode "svn-log-edit"
      "Wrapper around `log-edit-mode' for psvn.el"
      (easy-menu-add svn-log-edit-mode-menu)
      (setq svn-log-edit-update-log-entry nil)
      (set (make-local-variable 'log-edit-callback) 'svn-log-edit-done)
      (set (make-local-variable 'log-edit-listfun) 'svn-log-edit-files-to-commit)
      (set (make-local-variable 'log-edit-initial-files) (log-edit-files))
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
  (interactive)
  (svn-status-save-some-buffers)
  (save-excursion
    (set-buffer (get-buffer "*svn-log-edit*"))
    (when svn-log-edit-insert-files-to-commit
      (svn-log-edit-remove-comment-lines))
    (when (fboundp 'set-buffer-file-coding-system)
      (set-buffer-file-coding-system 'undecided-unix nil))
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
          (set-buffer "*svn-process*")
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
  (write-region (point-min) (point-max) svn-log-edit-file-name))

(defun svn-log-edit-erase-edit-buffer ()
  "Delete everything in the *svn-log-edit* buffer."
  (interactive)
  (set-buffer "*svn-log-edit*")
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
  (define-key svn-log-view-mode-map (kbd "=") 'svn-log-view-diff)
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
                    ["Edit log message" svn-log-edit-log-entry t]))

(defun svn-log-view-popup-menu (event)
  (interactive "e")
  (mouse-set-point event)
  (let* ((rev (svn-log-revision-at-point)))
    (when rev
      (svn-status-face-set-temporary-during-popup
       'svn-status-marked-popup-face (svn-point-at-bol) (svn-point-at-eol)
       svn-log-view-mode-menu))))

(defvar svn-log-view-font-lock-keywords
  '(("^r[0-9]+ .+" (0 `(face
                        font-lock-keyword-face
                        mouse-face
                        highlight
                        keymap ,svn-log-view-popup-menu-map))))
  "Keywords in svn-log-view-mode.")
(put 'svn-log-view-font-lock-keywords 'risky-local-variable t) ;for Emacs 20.7

(define-derived-mode svn-log-view-mode fundamental-mode "svn-log-view"
  "Major Mode to show the output from svn log.
Commands:
\\{svn-log-view-mode-map}
"
  (use-local-map svn-log-view-mode-map)
  (easy-menu-add svn-log-view-mode-menu)
  (set (make-local-variable 'font-lock-defaults) '(svn-log-view-font-lock-keywords t)))

(defun svn-log-view-next ()
  (interactive)
  (when (re-search-forward "^r[0-9]+" nil t)
    (beginning-of-line 3)))

(defun svn-log-view-prev ()
  (interactive)
  (when (re-search-backward "^r[0-9]+" nil t 2)
    (beginning-of-line 3)))

(defun svn-log-revision-at-point ()
  (save-excursion
    (re-search-backward "^r\\([0-9]+\\)")
    (svn-match-string-no-properties 1)))

(defun svn-log-view-diff (arg)
  "Show the changeset for a given log entry.
When called with a prefix argument, ask the user for the revision."
  (interactive "P")
  (let* ((upper-rev (svn-log-revision-at-point))
        (lower-rev (number-to-string (- (string-to-number upper-rev) 1)))
        (rev-arg (concat lower-rev ":" upper-rev)))
    (when arg
      (setq rev-arg (read-string "Revision for changeset: " rev-arg)))
    (svn-run nil t 'diff "diff" (concat "-r" rev-arg))
    (svn-status-activate-diff-mode)))

(defun svn-log-edit-log-entry ()
  "Edit the given log entry."
  (interactive)
  (let ((rev (svn-log-revision-at-point))
        (log-message))
    (svn-run nil t 'propget-parse "propget" "--revprop" (concat "-r" rev) "svn:log")
    (save-excursion
      (set-buffer "*svn-process*")
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

;; --------------------------------------------------------------------------------
;; svn-info-mode
;; --------------------------------------------------------------------------------
(defvar svn-info-mode-map () "Keymap used in `svn-info-mode' buffers.")
(put 'svn-info-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-info-mode-map)
  (setq svn-info-mode-map (make-sparse-keymap))
  (define-key svn-info-mode-map [?q] 'bury-buffer))

(defun svn-info-mode ()
  "Major Mode to view informative output from svn."
  (interactive)
  (kill-all-local-variables)
  (use-local-map svn-info-mode-map)
  (setq major-mode 'svn-info-mode)
  (setq mode-name "svn-info"))

;; --------------------------------------------------------------------------------
;; svn-process-mode
;; --------------------------------------------------------------------------------
(defvar svn-process-mode-map () "Keymap used in `svn-process-mode' buffers.")
(put 'svn-process-mode-map 'risky-local-variable t) ;for Emacs 20.7

(when (not svn-process-mode-map)
  (setq svn-process-mode-map (make-sparse-keymap))
  (define-key svn-process-mode-map [?q] 'bury-buffer))

(defun svn-process-mode ()
  "Major Mode to view process output from svn."
  (interactive)
  (kill-all-local-variables)
  (use-local-map svn-process-mode-map)
  (setq major-mode 'svn-process-mode)
  (setq mode-name "svn-process"))

;; --------------------------------------------------------------------------------
;; svn status persistent options
;; --------------------------------------------------------------------------------

(defun svn-status-base-dir (&optional start-directory)
  "Find the svn root directory for the current working copy.
Return nil, if not in a svn working copy."
  (let* ((base-dir (expand-file-name (or start-directory default-directory)))
         (dot-svn-dir (concat base-dir (svn-wc-adm-dir-name)))
         (in-tree (file-exists-p dot-svn-dir))
         (dir-below (expand-file-name default-directory)))
    (while (when (and dir-below (file-exists-p dot-svn-dir))
             (setq base-dir (file-name-directory dot-svn-dir))
             (string-match "\\(.+/\\).+/" dir-below)
             (setq dir-below
                   (and (string-match "\(.*/\)[^/]+/" dir-below)
                        (match-string 1 dir-below)))
             (setq dot-svn-dir (concat dir-below (svn-wc-adm-dir-name)))))
    (and in-tree base-dir)))

(defun svn-status-save-state ()
  "Save psvn persistent options for this working copy to a file."
  (interactive)
  (let ((buf (find-file (concat (svn-status-base-dir) "++psvn.state"))))
    (erase-buffer)        ;Widen, because we'll save the whole buffer.
    (setq svn-status-options
          (list
           (list "svn-trac-project-root" svn-trac-project-root)
           (list "sort-status-buffer" svn-status-sort-status-buffer)
           (list "elide-list" svn-status-elided-list)
           (list "module-name" svn-status-module-name)))
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
          (when (and (interactive-p) svn-status-elided-list (svn-status-apply-elide-list)))
          (message "psvn.el: loaded %s" file))
      (unless no-error (error "psvn.el: %s is not readable." file)))))

(defun svn-status-toggle-sort-status-buffer ()
  "Toggle sorting of the *svn-status* buffer.

If you turn off sorting, you can speed up \[svn-status].  However,
the buffer is not correctly sorted then.  This function will be
removed again, when a faster parsing and display routine for
`svn-status' is available."
  (interactive)
  (setq svn-status-sort-status-buffer (not svn-status-sort-status-buffer))
  (message "The %s buffer will %sbe sorted." svn-status-buffer-name
           (if svn-status-sort-status-buffer "" "not ")))

(defun svn-status-toggle-display-full-path ()
  "Toggle displaying the full path in the `svn-status-buffer-name' buffer"
  (interactive)
  (setq svn-status-display-full-path (not svn-status-display-full-path))
  (message "The %s buffer will%s use full path names." svn-status-buffer-name
           (if svn-status-display-full-path "" " not"))
  (svn-status-update))

(defun svn-status-set-trac-project-root ()
  (interactive)
  (setq svn-trac-project-root
        (read-string "Trac project root (e.g.: http://projects.edgewall.com/trac/): "
                     svn-trac-project-root))
  (when (yes-or-no-p "Save the new setting for svn-trac-project-root to disk? ")
    (svn-status-save-state)))

(defun svn-status-set-module-name ()
  "Interactively set svn-status-module-name."
  (interactive)
  (setq svn-status-module-name
        (read-string "Short Unit Name (e.g.: MyProject): "
                     svn-status-module-name))
  (when (yes-or-no-p "Save the new setting for svn-status-module-name to disk? ")
    (svn-status-save-state)))

(defun svn-browse-url (url)
  "Call `browse-url', using `svn-browse-url-function'."
  (let ((browse-url-browser-function (or svn-browse-url-function
                                         browse-url-browser-function)))
    (browse-url url)))

;; --------------------------------------------------------------------------------
;; svn status trac integration
;; --------------------------------------------------------------------------------
(defun svn-trac-browse-timeline ()
  "Open the trac timeline view for the current svn repository."
  (interactive)
  (unless svn-trac-project-root
    (svn-status-set-trac-project-root))
  (svn-browse-url (concat svn-trac-project-root "timeline")))

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
      (while (re-search-forward "^<<<<<<< .mine\n" nil t)
        (setq found t)
        (replace-match "")
        (if (not (re-search-forward "^=======\n" nil t))
            (error "Malformed conflict marker"))
        (replace-match "")
        (let ((start (point)))
          (if (not (re-search-forward "^>>>>>>> .r[0-9]+\n" nil t))
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
      (while (re-search-forward "^<<<<<<< .mine\n" nil t)
        (let ((start (match-beginning 0)))
          (if (not (re-search-forward "^=======\n" nil t))
              (error "Malformed conflict marker"))
          (delete-region start (point))
          (if (not (re-search-forward "^>>>>>>> .r[0-9]+\n" nil t))
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


(provide 'psvn)

;; Local Variables:
;; indent-tabs-mode: nil
;; End:
;;; psvn.el ends here
