/* 433-460 Human Language Technology Project
 *
 * Python interface to the MFCC feature extraction code written by Lin Zhong.
 *
 * Author: Peter Hawkins <hawkinsp@cs.mu.oz.au>
 * Student number: 119004
 */

#include <Python.h>
#include <Numeric/arrayobject.h>
#include <cstdio>
#include "SpeechProc.h"

/* Read a wave file and return a list of samples */
static PyObject *
mfcc_readwav(PyObject *self, PyObject *args)
{
    char *wavFile;
    featureParam FeatureParam;
    short *voiceData;
    unsigned int voiceLength;
    PyArrayObject *a;

    if (!PyArg_ParseTuple(args, "s", &wavFile))
        return NULL;

    SpeechProc getFeatures(FeatureParam);
    voiceData = getFeatures.ReadWav(wavFile, voiceLength);
    if (voiceData == NULL) {
        PyErr_SetString(PyExc_IOError, "File not found");
        return NULL;
    }

    int dimensions[1] = { voiceLength };

    a = (PyArrayObject *)PyArray_FromDims(1, dimensions, PyArray_SHORT);
    memcpy(a->data, voiceData, voiceLength * sizeof(short));

    delete[] voiceData;

    return (PyObject *)a;
}

/* mfcc_extractfeatures() - Given the filename of a wave file */
static PyObject *
mfcc_extractfeatures(PyObject *self, PyObject *args)
{
    char *wavFile;
    featureParam FeatureParam;
    unsigned int voiceLength, fn;
    short *voiceData;
    float **features;
    int i, j;
    PyObject *l, *t;

    if (!PyArg_ParseTuple(args, "s", &wavFile))
        return NULL;

    SpeechProc getFeatures(FeatureParam);
    voiceData = getFeatures.ReadWav(wavFile, voiceLength);
    if (voiceData == NULL) {
        PyErr_SetString(PyExc_IOError, "File not found");
        return NULL;
    }
    features = getFeatures.FeatureExtract(voiceData, voiceLength);

    delete[] voiceData;

    fn = getFeatures.GetFrameNum();

    l = PyList_New(fn);

    for (i = 0; i < (int)fn; i++) {
        t = PyList_New((int)FeatureParam.Cepstrum_order);
        for (j = 0; j < (int)FeatureParam.Cepstrum_order; j++) {
            PyList_SetItem(t, j, PyFloat_FromDouble((double)features[i][j]));
        }
        PyList_SetItem(l, i, t);
    }

    getFeatures.ReleaseFeatures();

    return l;
}

static PyMethodDef MfccMethods[] = {
    {"extractfeatures",  mfcc_extractfeatures, METH_VARARGS,
             "Extract MFCC features from a .WAV file."},
    {"readwav",  mfcc_readwav, METH_VARARGS,
             "Read data from a .WAV file."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


extern "C" {
    
PyMODINIT_FUNC
initmfcc(void)
{
        (void) Py_InitModule("mfcc", MfccMethods);
        import_array();
}

}
