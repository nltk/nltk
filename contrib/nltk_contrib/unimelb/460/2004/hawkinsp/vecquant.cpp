/* 433-460 Human Language Technology Project
 * Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
 * Student number: 119004
 *
 * This code is a C++ version of the vector quantization algorithm implemented
 * in vecquant.py. The Python version is too slow to be practical for a realistic
 * data set (typically 10^5 vectors), so this C++ implementation was created
 * instead.
 *
 * See the documentation in vecquant.py for a more complete description of the
 * algorithm.
 *
 */
#include <cstdio>

#include <cstdlib>
#include <cmath>
#include "pspeech.h"

static const double EPSILON = 0.01;
static const int MAX_VECTORS = 1500000;

int desired_codewords = 64;


/* Global variables. So shoot me. It's only a prototype. */
vector vecs[MAX_VECTORS];
int num_vectors = 0;

vector cwords[MAX_CODEWORDS];
int num_codewords;

int qval[MAX_VECTORS];

vector qvec[MAX_CODEWORDS];
int qc[MAX_CODEWORDS];


/* closest_codeword() - Given a vector of codewords and a vector id number,
 * return the identity of the codeword that is 'closest' to the vector under
 * a Euclidean distance metric.
 */
int closest_codeword(vector cwds[], int ncwds, int v)
{
    double best = 0.0;
    int best_index = -1, i;

    for (i=0; i< ncwds; i++) {
        vector d;
        double val;
        vec_sub(d, vecs[v], cwds[i]);
        val = vec_dot(d, d);

        if (best_index == -1 || val < best) {
            best = val;
            best_index = i;
        }
    }
    return best_index;
}

/* vecquant() - This routine performs the actual vector quantization
 * Global variables are used in lieu of arguments/return values since it allows
 * us to avoid using dynamic allocation.
 */
void vecquant(void)
{
    double d_av, cur_d_av, old_d_av;
    vector oldcwds[MAX_CODEWORDS], curcwds[MAX_CODEWORDS];

    num_codewords = 1;

    vec_zero(cwords[0]);
    for (int i = 0; i < num_vectors; i++) {
        vec_add(cwords[0], cwords[0], vecs[i]);
    }
    vec_scale(cwords[0], 1.0 / ((double) num_vectors));

//    vec_print(cwords[0]);
    

    d_av = 0.0;
    for (int i = 0; i < num_vectors; i++) {
        vector t;
        vec_sub(t, vecs[i], cwords[0]);
        d_av += vec_dot(t, t);
    }
    d_av /= ((double) num_vectors) * ((double) num_dimensions);

    while (num_codewords < desired_codewords) {
    //    printf("Splitting... %d\n", num_codewords);
        /* Split */
        for (int i = 0; i < num_codewords; i++) {
            vec_copy(curcwds[2*i + 1], cwords[i]);
            vec_scale(curcwds[2*i + 1], (1.0 - EPSILON));
            vec_copy(curcwds[2*i], cwords[i]);
            vec_scale(curcwds[2*i], (1.0 + EPSILON));
        }
        num_codewords *= 2;

        /* Iterate */
        cur_d_av = d_av;
        do {
//            printf("Iterating...\n");
            int j;
            for (j=0; j<num_codewords; j++) {
//                vec_print(curcwds[j]);
                qc[j] = 0;
                vec_zero(qvec[j]);
            }
            for (j=0; j< num_vectors; j++) {
                int c = closest_codeword(curcwds, num_codewords, j);
                qval[j] = c;
                vec_add(qvec[c], qvec[c], vecs[j]);
                qc[c]++;
            }

            for (j=0; j<num_codewords; j++) {
                vec_copy(oldcwds[j], curcwds[j]);
                /* The EPSILON is a fudge factor to avoid division by zero */
                vec_scale(qvec[j], 1.0 / (((double)qc[j]) + EPSILON));
                vec_copy(curcwds[j], qvec[j]);
                fprintf(stderr,"count %d = %d\n", j, qc[j]);
            }

            old_d_av = cur_d_av;

            
            cur_d_av = 0.0;
            for (int i = 0; i < num_vectors; i++) {
                vector t;
                vec_sub(t, vecs[i], oldcwds[qval[i]]);
                cur_d_av += vec_dot(t, t);
            }
            cur_d_av /= ((double) num_vectors) * ((double) num_dimensions);
        } while ((old_d_av - cur_d_av) / old_d_av > EPSILON);

        d_av = cur_d_av;

        for (int i=0;i<num_codewords;i++) {
            cwords[i] = curcwds[i]; 
        }
    }

}


int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "Need an argument (# codewords)\n");
        return EXIT_FAILURE;
    }
    desired_codewords = atoi(argv[1]);
    while (1) {
        if (num_vectors >= MAX_VECTORS) {
            fprintf(stderr, "Too many input vectors!\n");
            return EXIT_FAILURE;
        }
        
        fscanf(stdin, "[ ");
        if (feof(stdin)) break;
        for (int i = 0; i < num_dimensions; i++) {
            fscanf(stdin, "%lf", &vecs[num_vectors].c[i]);
            //printf("%f\n", vecs[num_vectors].c[i]);
            if (feof(stdin)) break;
        }
        fscanf(stdin, " ] ; ");
        num_vectors++;
    }

    // printf("Read %d vectors\n", num_vectors);

    vecquant();
    
//    printf("Produced %d codewords\n", num_codewords);

    printf("%d\n", num_codewords);
    for (int i = 0; i<num_codewords; i++) {
        for (int j = 0; j < num_dimensions; j++) {
            printf("%f ", cwords[i].c[j]);
        }
        printf("\n");
    }

    return 0;
}

