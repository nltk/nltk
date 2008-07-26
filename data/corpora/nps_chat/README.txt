README.txt for NPS Chat Corpus, Release 1.0 (July 2008)
===============================================================
Craig Martell
cmartell@nps.edu
http://faculty.nps.edu/cmartell

---------------------------------------------------------------
License and Legal Issues
---------------------------------------------------------------
This corpus is distributed solely for non-commercial, non-profit educational
and research use. It is a derivative compilation work of multiple works whose
copyrights are held by the respective original authors.


---------------------------------------------------------------
Description of the NPS Chat Corpus
---------------------------------------------------------------

The NPS Chat Corpus, Release 1.0 consists of 10,567 posts out of approximately
500,000 posts we have gathered from various online chat services in accordance
with their terms of service. Future releases will contain more posts from more
domains. New releases will be announced and described at

http://faculty.nps.edu/cmartell/NPSChat.htm.

The posts included in Release 1.0 have been:

1) Hand privacy masked;
2) Part-of-speech tagged; and
3) Dialogue-act tagged.

The posts have been privacy masked in two ways. Firstly, all usernames have
been changed to generic names of the form "UserN", where N is a unique integer
consistently used for each respective poster across all files. Secondly, the
posts have been read by humans to remove other personally identifiable
information.

All of the recordings included with this release are from age-specific chat
rooms. Each file is a recording from one of these chat rooms for a short
period on a particular day. The filename contains all this information plus
the number of posts contained in the file. For example, the file
10-19-20s_706posts.xml contains 706 posts gathered from the 20s chat room on
10/19/2006. All data released here was gathered in 2006. Please note that
within each file usernames get prepended with the date and chat-room portions
of the filename. So, UserN becomes 10-19-20sUserN.

As of release 1.0, the POS tag set is the Penn Treebank tag set. We are in the
process of modifying the tag set to make it more chat specific, and hope to
implement these changes in future releases. For example, conversational
initialisms, like LOL, BRB, should have their own tag (CI). But we currently
simply tag them as interjections (UH).

The dialogue-act tags are Accept, Bye, Clarify, Continuer, Emotion, Emphasis,
Greet, No Answer, Other, Reject, Statement, System, Wh-Question, Yes Answer,
Yes/No Question. (See [2] and [3], below.)

The NPS Chat Corpus was created by Eric Forsyth, Jane Lin, and Craig Martell.
Please use [1], below, when referring to the NPS Chat Corpus.

Please address all questions to Craig Martell (cmartell@nps.edu).

---------------------------------------------------------------
Files in the corpus
---------------------------------------------------------------
10-19-20s_706posts.xml
10-19-30s_705posts.xml
10-19-40s_686posts.xml
10-19-adults_706posts.xml
10-24-40s_706posts.xml
10-26-teens_706posts.xml
11-06-adults_706posts.xml
11-08-20s_705posts.xml
11-08-40s_706posts.xml
11-08-adults_705posts.xml
11-08-teens_706posts.xml
11-09-20s_706posts.xml
11-09-40s_706posts.xml
11-09-adults_706posts.xml
11-09-teens_706posts.xml
README.txt
postClassPOSTagset.xsd

---------------------------------------------------------------
Refernces
---------------------------------------------------------------
[1] Eric N. Forsyth and Craig H. Martell, "Lexical and Discourse Analysis of
Online Chat Dialog," Proceedings of the First IEEE International Conference on
Semantic Computing (ICSC 2007), pp. 19-26, September 2007.

[2] T. Wu, F. M. Khan, T. A. Fisher, L. A. Shuler and W. M. Pottenger,
"Posting act tagging using transformation-based learning," Proceedings of the
Workshop on Foundations of Data Mining and Discovery, IEEE International
Conference on Data Mining, December 2002.

[3] A. Stolcke, K. Ries, N. Coccaro, E. Shriberg, R. Bates, D. Jurafsky, P.
Taylor, R. Martin, C. Van Ess-Dykema and M. Meteer, "Dialogue act modeling for
automatic tagging and recognition of conversational speech," Computational
Linguistics, vol. 26, no. 3, pp. 339-373, 2000.
