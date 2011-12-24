/* 
 * Command-line interface to mallet's CRF, used by NLTK.
 *
 * Options:
 *  --model-file FILE    -- zip file containing crf-info.xml and 
 *                          crf-model.ser (serialized mallet CRF model).
 *  --test-file FILE     -- test data filename: one token per line,
 *                          sequences seperated by newlines.
 *
 * Results are written to stdout.
 *
 * Copyright (C) 2001-2012 NLTK Project
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://www.nltk.org/>
 * For license information, see LICENSE.TXT
 */

package org.nltk.mallet;

import edu.umass.cs.mallet.base.types.*;
import edu.umass.cs.mallet.base.fst.*;
import edu.umass.cs.mallet.base.minimize.*;
import edu.umass.cs.mallet.base.minimize.tests.*;
import edu.umass.cs.mallet.base.pipe.*;
import edu.umass.cs.mallet.base.pipe.iterator.*;
import edu.umass.cs.mallet.base.pipe.tsf.*;
import edu.umass.cs.mallet.base.util.*;
import junit.framework.*;
import java.util.Iterator;
import java.util.Random;
import java.util.regex.*;
import java.util.logging.*;
import java.io.*;
import java.util.zip.*;

public class RunCRF
{
    private static Logger logger =
        MalletLogger.getLogger(RunCRF.class.getName());

    /**
     * RunCRF may not be instantiated.
     */
    private RunCRF() {}


    // Regexp constant.
    private static Pattern blankline = Pattern.compile("^\\s*$");

    //////////////////////////////////////////////////////////////////
    // Option definitions.  
    //////////////////////////////////////////////////////////////////

    private static final CommandOption.File modelFileOption =
        new CommandOption.File
        (SimpleTagger.class, "model-file", "FILENAME", true, null,
         "The filename for the model.", null);

    private static final CommandOption.File testFileOption =
        new CommandOption.File
        (RunCRF.class, "test-file", "FILENAME", true, null,
         "The filename for the testing data.", null);
    
    private static final CommandOption.List commandOptions =
        new CommandOption.List (
                                "Run the CRF4 tagger",
                                new CommandOption[] {
                                    modelFileOption,
                                    testFileOption
                                });

    //////////////////////////////////////////////////////////////////
    // Command-line interface.
    //////////////////////////////////////////////////////////////////

    public static void main (String[] args) throws Exception
    {
        Reader trainingFile = null, testFile = null;
        InstanceList trainingData = null, testData = null;
        Pipe p = null;
        CRF4 crf = null;

        int numEvaluations = 0;
        int iterationsBetweenEvals = 16;
        int restArgs = commandOptions.processOptions(args);

        // Check arguments
        if (restArgs != args.length) {
            commandOptions.printUsage(true);
            throw new IllegalArgumentException("Unexpected arg "+
                                               args[restArgs]);
        }
        if (testFileOption.value == null) {
            commandOptions.printUsage(true);
            throw new IllegalArgumentException("Expected --test-file FILE");
        }
        if (modelFileOption.value == null) {
            commandOptions.printUsage(true);
            throw new IllegalArgumentException("Expected --model-file MODEL");
        }

        // Load the classifier model.
        ZipFile zipFile = new ZipFile(modelFileOption.value);
        ZipEntry zipEntry = zipFile.getEntry("crf-model.ser");
        ObjectInputStream s =
            new ObjectInputStream(zipFile.getInputStream(zipEntry));
        crf = (CRF4) s.readObject();
        s.close();

        // Look up the pipe used to generate feature vectors.
        p = crf.getInputPipe();

        // The input file does not contain tags (aka targets)
        p.setTargetProcessing(false);

        // Open the test file.
        testFile = new FileReader(testFileOption.value);

        // Create a new instancelist to hodl the test data.
        testData = new InstanceList(p);

        // Read in the test data.
        testData.add(new LineGroupIterator(testFile, blankline, true));

        // Print the results.
        for (int i=0; i<testData.size(); i++) {
            // Get the input value.
            Sequence input = (Sequence)testData.getInstance(i).getData();
            // Run the CRF model.
            Sequence output = crf.transduce(input);
            // Sanity check: size should match.
            if (output.size() != input.size())
                throw new Exception("Failed to decode "+i+", got"+output);
            // Display the tags, one per line.
            for (int j = 0; j < input.size(); j++)
                System.out.println(output.get(j).toString());
            // Add a blank line to seperate instances.
            System.out.println();
        }
    }
}
