/**
 * tts: Python extension module for Festival Speech Synthesis System
 *
 * Author: David Zhang <dlz@students.cs.mu.oz.au>
 * 	   Steven Bird <sb@cs.mu.oz.au>
 * URL: <http://nltk.sf.net>
 * For license information, see LICENSE.TXT
 *
 * Much of this code is the result of amalgamating the recipes given by the
 * Python/C API specification and the Festival/C API specification. Minimal
 * error-checking is included.
 *
 * For more information, refer to the following resources.
 *
 * Python:	http://www.python.org/doc/current/ext/ext.html
 * Festival:	http://festvox.org/docs/manual-1.4.3/festival_toc.html
 **/


/* Festival C API */
/* If the compiler cannot find this file, ensure that the -I include path is
   set correctly and contains the Festival include path */
#include "festival.h"

/* Python C API */
#include <python2.1/Python.h>


/**
 * Initializes Festival. This must be called before any function.
 * It can be called with no arguments (in which case default values are used)
 * or both arguments must be supplied.
 * @param heap_size Scheme heap size
 * @param load_init_files Load init files?
 **/
PyObject *tts_initialize(PyObject *self, PyObject *args)
{
	int heap_size;
	int load_init_files;

	// No arguments: Use default values
	if (PyArg_ParseTuple(args, ""))
	{
		heap_size = 210000;	// Default heap size
		load_init_files = 1;	// Default is to load init files
	}

	// Parse arguments
	else if (!PyArg_ParseTuple(args, "ii", &heap_size, &load_init_files))
		return NULL;

	// Initialize Festival
	festival_initialize( load_init_files, heap_size );

	// Return "void"
	return Py_BuildValue("");
}


/**
 * Say the contents of a file.
 * @param file the name of the file to read
 **/
PyObject *tts_say_file(PyObject *self, PyObject *args)
{
	char *file = "None";

	// Parse arguments
	if (!PyArg_ParseTuple(args, "s", &file))
		return NULL;

	// Say Text
	festival_say_file(file);

	// Return "void"
	return Py_BuildValue("");
}


/**
 * Say the contents of a string.
 * @param text the text to be read
 **/
PyObject *tts_say_text(PyObject *self, PyObject *args)
{
	char *text = "None";

	// Parse arguments
	if (!PyArg_ParseTuple(args, "s", &text))
		return NULL;

	// Say Text
	festival_say_text(text);

	// Return "void"
	return Py_BuildValue("");
}


/**
 * Synthesizes the string into a wave file.
 * @param text the text to be read
 * @param file the name of the wave file to save to
 **/
PyObject *tts_text_to_wave(PyObject *self, PyObject *args)
{
	EST_Wave wave;
	char *text = "None";
	char *file = "None";

	// Parse arguments
	if (!PyArg_ParseTuple(args, "ss", &text, &file))
		return NULL;

	// Generate wave file
	festival_text_to_wave(text, wave);
	wave.save(file, "riff");

	// Return "void"
	return Py_BuildValue("");
}


/**
 * The following is required for the Python extension module. For more
 * information, refer to the Python documentation.
 **/

/* Method table */
static PyMethodDef ttsmethods[] =
{
	{ "initialize", tts_initialize, METH_VARARGS, "Initializes the Festival engine" },
	{ "say_file", tts_say_file, METH_VARARGS, "Say the contents of a file" },
	{ "say_text", tts_say_text, METH_VARARGS, "Say the contents of a string" },
	{ "text_to_wave", tts_text_to_wave, METH_VARARGS, "Synthesizes a string into a wave" },
	{ NULL, NULL, 0, NULL }
};


/* Module initialization function */
extern "C" void inittts(void)
{
	// Initialize Python Module
	Py_InitModule("tts", ttsmethods);
}
