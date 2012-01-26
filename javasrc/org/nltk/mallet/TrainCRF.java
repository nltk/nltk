/*
 * Command-line interface to mallet's CRF, used by NLTK.
 *
 * Options:
 *  --model-file FILE    -- zip file containing crf-info.xml.
 *  --train-file FILE    -- training data filename: one token per line,
 *                          sequences seperated by newlines.
 *
 * Copyright (C) 2001-2012 NLTK Project
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://www.nltk.org/>
 * For license information, see LICENSE.TXT
 */

package org.nltk.mallet;

import java.io.*;
import java.util.logging.*;
import java.util.regex.*;
import java.util.*;
import java.util.zip.*;

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

     private static final CommandOption.File trainFileOption =
         new CommandOption.File
         (TrainCRF.class, "train-file", "FILENAME", true, null,
          "The filename for the training data.", null);

     private static final CommandOption.File modelFileOption =
         new CommandOption.File
         (TrainCRF.class, "model-file", "FILENAME", true, null,
          "The CRF model file, a zip file containing crf-info.xml."+
          "TrainCRF will add crf-model.ser to this file.", null);

    private static final CommandOption.List commandOptions =
        new CommandOption.List 
        ("Train a CRF tagger.",
         new CommandOption[] {
             trainFileOption,
             modelFileOption});


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

        // Set up the weight groups.
        if (crfInfo.weightGroupInfoList != null) {
            Iterator wgIter = crfInfo.weightGroupInfoList.iterator();
            while (wgIter.hasNext()) {
                CRFInfo.WeightGroupInfo wg = (CRFInfo.WeightGroupInfo)
                    wgIter.next();
                FeatureSelection fs = FeatureSelection.createFromRegex
                    (crf.getInputAlphabet(), 
                     Pattern.compile(wg.featureSelectionRegex));
                crf.setFeatureSelection(crf.getWeightsIndex(wg.name), fs);
            }
        }

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
            throw new IllegalArgumentException("Expected --model-file FILE");
        }

        // Get the CRF structure specification.
        ZipFile zipFile = new ZipFile(modelFileOption.value);
        ZipEntry zipEntry = zipFile.getEntry("crf-info.xml");
        CRFInfo crfInfo = new CRFInfo(zipFile.getInputStream(zipEntry));
        
        StringBuffer crfInfoBuffer = new StringBuffer();
        BufferedReader reader = new BufferedReader(
            new InputStreamReader(zipFile.getInputStream(zipEntry))); 
        String line;
        while ((line = reader.readLine()) != null) {
            crfInfoBuffer.append(line).append('\n');
        }
        reader.close();                   

        // Create the CRF, and train it.
        CRF4 crf = createCRF(trainFileOption.value, crfInfo);
        
        // Create a new zip file for our output.  This will overwrite
        // the file we used for input.
        ZipOutputStream zos = 
            new ZipOutputStream(new FileOutputStream(modelFileOption.value));
                    
        // Copy the CRF info xml to the output zip file.
        zos.putNextEntry(new ZipEntry("crf-info.xml"));
        BufferedWriter writer = new BufferedWriter(
            new OutputStreamWriter(zos));
        writer.write(crfInfoBuffer.toString());
        writer.flush();
        zos.closeEntry();

        // Save the CRF classifier model to the output zip file.
        zos.putNextEntry(new ZipEntry("crf-model.ser"));
        ObjectOutputStream oos = 
            new ObjectOutputStream(zos);
        oos.writeObject(crf);
        oos.flush();
        zos.closeEntry();
        zos.close();
    }
}

