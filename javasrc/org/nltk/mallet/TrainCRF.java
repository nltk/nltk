/*
 * java TrainCRF --model-file FILE --crf-info FILE --train-file FILE
 */

package org.nltk.mallet;

import java.io.*;
import java.util.logging.*;
import java.util.regex.*;
import java.util.*;

import edu.umass.cs.mallet.base.types.*;
import edu.umass.cs.mallet.base.fst.*;
import edu.umass.cs.mallet.base.pipe.*;
import edu.umass.cs.mallet.base.pipe.iterator.*;
import edu.umass.cs.mallet.base.util.*;

import org.nltk.mallet.*;

public class TrainCRF
{
    //////////////////////////////////////////////////////////////////
    // Option definitions.
    //////////////////////////////////////////////////////////////////

     private static final CommandOption.File modelFileOption =
         new CommandOption.File
         (TrainCRF.class, "model-file", "FILENAME", true, null,
          "The filename for the model.", null);

     private static final CommandOption.File trainFileOption =
         new CommandOption.File
         (TrainCRF.class, "train-file", "FILENAME", true, null,
          "The filename for the training data.", null);

     private static final CommandOption.File crfInfoFileOption =
         new CommandOption.File
         (TrainCRF.class, "crf-info", "FILENAME", true, null,
          "The CRF structure specification file.", null);

    private static final CommandOption.List commandOptions =
        new CommandOption.List 
        ("Train a CRF tagger.",
         new CommandOption[] {
             modelFileOption,
             trainFileOption,
             crfInfoFileOption});


    //////////////////////////////////////////////////////////////////
    // CRF Creation
    //////////////////////////////////////////////////////////////////

    public static CRF4 createCRF(File trainingFile, CRFInfo crfInfo) 
                               throws FileNotFoundException
    {
        Reader trainingFileReader = new FileReader(trainingFile);

        // Create a pipe that we can use to convert the training
        // file to a feature vector sequence.
        Pipe p = new SimpleTagger.SimpleTaggerSentence2FeatureVectorSequence();

        // The training file does contain tags (aka targets)
        p.setTargetProcessing(true);

        // Register the default tag with the pipe, by looking it up
        // in the targetAlphabet before we look up any other tag.
        p.getTargetAlphabet().lookupIndex(crfInfo.defaultLabel);

        // Create a new instancelist to hold the training data.
        InstanceList trainingData = new InstanceList(p);

        // Read in the training data.
        trainingData.add(new LineGroupIterator
                         (trainingFileReader, 
                          Pattern.compile("^\\s*$"), true));

        // Create the CRF model.
        CRF4 crf = new CRF4(p, null);

        // Set various config options
        crf.setGaussianPriorVariance(crfInfo.gaussianVariance);
        crf.setTransductionType(crfInfo.transductionType);

        // Set up the model's states.
        if (crfInfo.stateInfoList != null) {
            Iterator stateIter = crfInfo.stateInfoList.iterator();
            while (stateIter.hasNext()) {
                CRFInfo.StateInfo state = (CRFInfo.StateInfo) stateIter.next();
                crf.addState(state.name, state.initialCost, state.finalCost,
                             state.destinationNames, state.labelNames,
                             state.weightNames);
            }
        }
        else if (crfInfo.stateStructure == CRFInfo.FULLY_CONNECTED_STRUCTURE)
            crf.addStatesForLabelsConnectedAsIn(trainingData);
        else if (crfInfo.stateStructure == CRFInfo.HALF_CONNECTED_STRUCTURE)
            crf.addStatesForHalfLabelsConnectedAsIn(trainingData);
        else if (crfInfo.stateStructure == 
                 CRFInfo.THREE_QUARTERS_CONNECTED_STRUCTURE)
            crf.addStatesForThreeQuarterLabelsConnectedAsIn(trainingData);
        else if (crfInfo.stateStructure == CRFInfo.BILABELS_STRUCTURE)
            crf.addStatesForBiLabelsConnectedAsIn(trainingData);
        else
            throw new RuntimeException("Unexpected state structure "+
                                       crfInfo.stateStructure);

        // Add a start state, and set the initial costs for all other
        // states to POSITIVE_INFINITY??
        /*[xxx]*/

        // Train the CRF.
        crf.train (trainingData, null, null, null, crfInfo.maxIterations);

        return crf;
    }

    /** This is (mostly) copied from CRF4.java */
    public boolean[][] labelConnectionsIn(Alphabet outputAlphabet, 
                                          InstanceList trainingSet,
                                          String start)
    {
        int numLabels = outputAlphabet.size();
        boolean[][] connections = new boolean[numLabels][numLabels];
        for (int i = 0; i < trainingSet.size(); i++) {
            Instance instance = trainingSet.getInstance(i);
            FeatureSequence output = (FeatureSequence) instance.getTarget();
            for (int j = 1; j < output.size(); j++) {
                int sourceIndex = outputAlphabet.lookupIndex (output.get(j-1));
                int destIndex = outputAlphabet.lookupIndex (output.get(j));
                assert (sourceIndex >= 0 && destIndex >= 0);
                connections[sourceIndex][destIndex] = true;
            }
        }

        // Handle start state
        if (start != null) {
            int startIndex = outputAlphabet.lookupIndex (start);
            for (int j = 0; j < outputAlphabet.size(); j++) {
                connections[startIndex][j] = true;
            }
        }

        return connections;
    }

    //////////////////////////////////////////////////////////////////
    // Command-line interface.
    //////////////////////////////////////////////////////////////////

    public static void main (String[] args) throws Exception
    {
        Reader trainingFile = null;

        // Process arguments
        int restArgs = commandOptions.processOptions(args);

        // Check arguments
        if (restArgs != args.length) {
            commandOptions.printUsage(true);
            throw new IllegalArgumentException("Unexpected arg "+
                                               args[restArgs]);
        }
        if (trainFileOption.value == null) {
            commandOptions.printUsage(true);
            throw new IllegalArgumentException("Expected --train-file FILE");
        }
        if (modelFileOption.value == null) {
            commandOptions.printUsage(true);
            throw new IllegalArgumentException("Expected --model-file MODEL");
        }
        if (crfInfoFileOption.value == null) {
            commandOptions.printUsage(true);
            throw new IllegalArgumentException("Expected --crf-info XMLFILE");
        }

        // Get the CRF structure specification.
        CRFInfo crfInfo = new CRFInfo(crfInfoFileOption.value);

        // Create the CRF, and train it.
        CRF4 crf = createCRF(trainFileOption.value, crfInfo);

        // Save the CRF classifier model to disk.
        ObjectOutputStream s =
            new ObjectOutputStream(
                new FileOutputStream(modelFileOption.value));
        s.writeObject(crf);
        s.flush();
        s.close();
    }
}

