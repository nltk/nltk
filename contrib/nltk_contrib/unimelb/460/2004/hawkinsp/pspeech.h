/* 433-460 Human Language Technology Project
 * Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
 * Student number: 119004
 * 
 * Common function prototypes and definitions for C++ code
 */

static const int MAX_DIMENSIONS = 16;
static const int num_dimensions = 12;
struct vector {
        double c[MAX_DIMENSIONS];
};

static const int MAX_CODEWORDS = 128;


void vec_zero(vector& v);
void vec_copy(vector& dest, const vector& a);
void vec_add(vector& dest, const vector& a, const vector& b);
void vec_sub(vector& dest, const vector& a, const vector& b);
void vec_scale(vector &v, double x);
double vec_dot(const vector& a, const vector& b);
void vec_print(const vector& a);

