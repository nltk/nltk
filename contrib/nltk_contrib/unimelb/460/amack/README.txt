		pull_out_stops.pl takes as an argument a list of (newline-separated) stopwords to be removed and removes any such words if they match a line received via standard input, printing the remainder to standard output. A list of newline-separated potential search terms is redirected into the module from a Swadesh list taken from the Rosetta site (after some manual refinement to standardise the data). Swadesh lists (listed by ethnologue code, with suffix 'utf-8') are provided for all of the test languages in the report as well as for a few additional languages


		do_search.py receives a list of search terms from standard input (usually piped from \code{pull_out_stops.pl) and performs a Google query using the Google Web API, printing the query results to standard output.


		fetch_text.py takes a the result of Google web API queries from standard input, parses it to extract the query term, number of results and all of the returned URLs and fetches those URLs as plaintext by using the command 'lynx -dump' and piping the output to 'strip_non_std.py'. It outputs a list of uniquely-numbered filenames containing the fetched text and an auxilary file (suffix '.info') containing the the URL and the search term which produced it along with the number of Google hits the term returned. Prepended to the filename is a representation of the number of hits so the filesystem will sort them in an increasing fashion. The representation is actually 'f' followed by the 2-digit rounded integer corresponding to (10*log10(h)) for 'h' hits. There is a suffix on the file of 't' followed by three digits incidicating the ordinal index of the term which produced the first hit.


		strip_non_std.py is a utility to further remove non-plaintext web-page artefacts (URLs, image locations etc.) from returned pages that still remain after the pages are fetched with \code{lynx -dump.
		

		loc_lookup.py takes the following parameters:
			-l locodes_path	
			The location of a copy of the UN LoCODES database. (On dog: /nlptools/loc051cs/UNLOCODE_CodeList_2005-1.csv)
			
			-c expected_countries_file
			The location of a file listing the countries where the language is known to be spoken. (Provided as an ethnologue code with a 'exp_cnt' suffix)
			
			-t textcat_path
			The path of a local copy of TextCat. (On dog: /nlptools/textcat/text_cat)

			-s file_suff
			Use the given suffix on files which have an appropriate location
			
		It first obtains a list of locations in the target countries from the LoCODES file, then receives a list of filenames from standard input and runs the Unix tool \code{grep on each file searching for any location in the list. If one of the locations appears the file is tagged with a suffix file_suff (usually 'llp' for 'location-lookup positive') to indicate that it is a likely sample. All such samples are then tested with \code{Textcat and tagged to indicate whether it could unmbiguously determine the language of the document ('ktc' for known by TextCat; 'utc' for unknown by TextCat).
		

		test_textcat.py simply performs the Textcat test on any arguments it receives (for examining the residue). Suffixes: 'ktc' for known by TextCat; 'utc' for unknown by TextCat.


		WordUnigramEntropyEstimator.py takes the following parameters:

			-l training_file_name
			If provided, first load the distribution from the training file.
			
			-t training_file_name
			If provided, use training mode: All input data is assumed to be training data. Save the distribution to the training file after training on input data.

			-w n
			Get the top 'n' words from the probability distribution being used at the final stage.
		It either updates a probability distribution on the basis of command-line filename arguments and saves it to the file specified or loads a previously created distribution and determines the cross-entropy $H$ of each file argument with respect to this distribution. The output is a list of filenames and corresponding $H$ value sorted by increasing $H$.
		
		loc_lookup_known.py is similar to \code{loc_lookup.py but was used in the testing phase when experimenting on known languages. Textcat is used differently; there is another parameter '-e' for the expected textcat output.
		
		ScoreEntCutoffs.py is also used in this to produce the results for the known test languages
			-r suffix for correctly classified files
			-w suffix for incorrectly classified files
			-d number of divisions for the cutoffs (default 10)
			-a alpha value for the F-score
		
		Additionally there are some shell scripts to automate the whole process.
		Arguments for lang_sample_fetcher.sh
		lang_sample_fetcher.sh testname swadesh_list exp_countries_file 
		and an additional argument '-c' for trying the queries in every possible combination (used in iteration 2) and an extra url_dict argument for loading a dictionary of  URLs already retrieved)

		Suggested Usage for language with ethnologue code XXX and test number NN
		1. create a directory for the test
		2. change to that directory
		3. run 'lang_sample_fetcher.sh XXX_NN ../XXX.utf-8 ../XXX_exp_cnt'
		4. run 'more *.llp.utc*' to get a listing of every file fetched in order of increasing google hits and the corresponding auxiliary file (.info) containing the url it came from
		5. select a valid sample VALID
		6. run '../WordUnigramEntropyEstimator.py -t train.VALID VALID'
		7. run '../WordUnigramEntropyEstimator.py -l train.VALID *.llp.utc' > train.VALID.res
		8. examine the documents in order of cross entropy to determine the possible matches (use '../piped_arg_ops.py more - < train.VALID.res > XXX_NN.poss_docs' to get all of the possible documents in order of entropy into a single document for easy examination. You now have a list of some valid samples and the first iteration is complete.
		9. if desired edit train.VALID.res to produce a single list of training documents XXX_NN.likely_docs
		10. if desired retrain using '../WordUnigramEntropyEstimator.py -t train.XXX_NN.likely_docs  < XXX_NN.likely_docs'
		11. get a list of likely words using '../WordUnigramEntropyEstimator.py -l train.XXX_NN.likely_docs -w 20 > XXX_NN.likely_words'
		12. run '../pull_out_stops.pl ../stop_words < XXX_NN.likely_words | XXX_NN_i2.query_words' to determine how many remain after stopword removal, the cull the list down to 5 or 7
		13. run 'make_url_dict.py -o XXX_NN.url_dict *.info' to make a dictionary of visited URLs
		14.  run 'lang_sample_fetcher.sh XXX_NN_i2  XXX_NN_i2.query_words ../XXX_exp_cnt -c XXX_NN.url_dict'
		15. this wil give another list of documents which can then be examined by repeating steps 7 and 8, with *i2*.llp.utc as training data in step 7.

		All the messy test data can be found on dog in /home/amack/lid
		(look for directories starting with 'test_')


