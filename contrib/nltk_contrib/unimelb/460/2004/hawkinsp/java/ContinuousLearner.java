/* 433-460 Human Language Technology Project
 * Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
 * Student number: 119004
 *
 * HMM learning code. Given a list of training data files with names of the form
 * q_YY.vec where YY is the two letter word identification string, use the
 * Segmental K-Means HMM learning algorithm to construct an continuous
 * probability density HMM that recognises each word.
 *
 * This code is written in Java to avoid having to implement Segmental K-Means
 * in Python. Empirically this algorithm appears to perform much better than
 * the Baum-Welch algorithm, especially for continuous probability density
 * HMMs.
 */

import java.util.*;
import java.io.*;
import be.ac.ulg.montefiore.run.jahmm.*;
import be.ac.ulg.montefiore.run.jahmm.Hmm.*;
import be.ac.ulg.montefiore.run.jahmm.learn.*;
import be.ac.ulg.montefiore.run.jahmm.io.*;
import be.ac.ulg.montefiore.run.jahmm.draw.*;


class ContinuousRecognizer {
    public Hmm hmm;
    private int nb_states, nb_dimensions;

    public ContinuousRecognizer(String w, int nstates, int ndimensions) 
            throws java.io.IOException {
        nb_states = nstates;
        nb_dimensions = ndimensions;

        Vector obs_seqs = new Vector();

        Reader reader = new FileReader("q_" + w + ".vec");
        obs_seqs = ObservationSequencesIO.readSequences(
                new ObservationVectorIO(),
                reader
        );
        reader.close();

   
/*        System.out.println(Integer.toString(obs_seqs.size()) +
                " observation sequences for word " + w);
        System.out.println("Learning an HMM for word " + w); */

        KMeansLearner kml = new KMeansLearner(nb_states,
                new OpdfMultiGaussianFactory(nb_dimensions), obs_seqs);
        /* Only iterate 3 or so times to avoid overfitting. */
        hmm = kml.iterate();
        hmm = kml.iterate();
        hmm = kml.iterate();
        

//        (new HmmIntegerDrawer()).write(hmm, word + ".dot");
    }

    double probability(Vector oseq) {
        return hmm.lnProbability(oseq);
    }
}

public class ContinuousLearner {
    public static final int nb_states = 6;
    public static final int nb_dimensions = 12;
    public static final String words[] = {
            "00", "01", "02", "03", "04", "05", "06", "07", "08", "09",
            "en", "er", "go", "hp", "no", "rb", "rp", "sp", "st", "ys"
    };

    public static void main(String[] args) throws java.io.IOException {
        ContinuousRecognizer recogs[] = new ContinuousRecognizer[words.length];

        System.out.print(
                    "mean = [[[] for i in range(" +
                    Integer.toString(nb_states) + ")] for j in range(" +
                    Integer.toString(words.length) + ")]\n" +
                    "covar = [[[] for i in range(" +
                    Integer.toString(nb_states) + ")] for j in range(" +
                    Integer.toString(words.length) + ")]\n" +
                    "A = [[] for i in range(" +
                    Integer.toString(words.length) + ")]\n" +
                    "Pi = [[] for i in range(" +
                    Integer.toString(words.length) + ")]\n");

        for (int w = 0; w < words.length; w++) {
            recogs[w] = new ContinuousRecognizer(words[w], nb_states, nb_dimensions);

            // State probability distributions
            
            for (int s=0; s<nb_states; s++) {
                // Mean vector
                System.out.print("mean[" + Integer.toString(w) + "][" + Integer.toString(s) + "] = [");
                for (int q=0;q<nb_dimensions; q++) {
                 System.out.print(
                    ((OpdfMultiGaussian)
                     recogs[w].hmm.getOpdf(s)).getDistribution().mean[q]);
                 System.out.print(", ");
                }
                System.out.println("]");

                // Covariance matrix
                System.out.print("covar[" + Integer.toString(w) + "]["
                        + Integer.toString(s) + "] = [");
                for (int x=0;x<nb_dimensions; x++) {
                    System.out.print("[");
                    for (int y=0;y<nb_dimensions; y++) {
                        System.out.print(
                                ((OpdfMultiGaussian)
                                 recogs[w].hmm.getOpdf(s)).getDistribution().covariance[x][y]);
                        if (y != 11) {
                            System.out.print(", ");
                        } else {
                            System.out.println("],");

                        }
                    }
                }
                System.out.println("]");
            }
            // A_ij array
            System.out.print("A[" + Integer.toString(w) + "] = [");
            for (int i=0; i<nb_states; i++) {
                System.out.print("[");
                for (int j=0; j<nb_states; j++) {
                    System.out.print(recogs[w].hmm.getAij(i, j));
                    System.out.print(", ");
                }
                System.out.println("],");
            }
            System.out.println("]");

            // Pi array
            System.out.print("Pi[" + Integer.toString(w) + "] = [");
            for (int i=0; i<nb_states; i++) {
                System.out.print(recogs[w].hmm.getPi(i));
                System.out.print(", ");
            }
            System.out.println("]");
                
        }

    }
}

