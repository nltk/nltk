/* 433-460 Human Language Technology Project
 * Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
 * Student number: 119004
 *
 * Library of functions to handle basic vector operations.
 *
 * Note that this is C++ code, although it is not object-oriented C++ code.
 */
#include <cstdio>
#include "pspeech.h"

/* Vector manipulation functions */
void vec_zero(vector& v)
{
    for (int i = 0; i < num_dimensions; i++) {
        v.c[i] = 0.0;
    }
}

/* Add src to dest, store the result in dest */
void vec_copy(vector& dest, const vector& a)
{
    for (int i = 0; i < num_dimensions; i++) {
        dest.c[i] = a.c[i];
    }
}
void vec_add(vector& dest, const vector& a, const vector& b)
{
    for (int i = 0; i < num_dimensions; i++) {
        dest.c[i] = a.c[i] + b.c[i];
    }
}

void vec_sub(vector& dest, const vector& a, const vector& b)
{
    for (int i = 0; i < num_dimensions; i++) {
        dest.c[i] = a.c[i] - b.c[i];
    }
}

void vec_scale(vector &v, double x)
{
    for (int i = 0; i < num_dimensions; i++) {
        v.c[i] *= x;
    }
}

double vec_dot(const vector& a, const vector& b)
{
    double result = 0;
    for (int i = 0; i < num_dimensions; i++) {
        result += a.c[i] * b.c[i];
    }
    return result;
}

void vec_print(const vector& a)
{
    for (int i = 0; i < num_dimensions; i++) {
        printf("%f ", a.c[i]);
    }
    printf("\n");
}
