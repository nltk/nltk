/* Natural Language Toolkit: C Implementation of nltk.token
 *
 * Copyright (C) 2003 University of Pennsylvania
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://nltk.sourceforge.net>
 * For license information, see LICENSE.TXT
 *
 * $Id$
 *
 * This module provides a drop-in replacement for the Location and
 * Token classes.  Since these classes are used extensively in NLTK
 * (for Tokens), this C implementation can give a signifigant
 * performance boost.
 *
 * Compilation of this extension is handled by NLTK's setup.py script.
 * To test this module, use NLTK's setup.py script to build it:
 *     % python setup.py build
 *
 * This will create a "build" directory, containing the file
 * "build/lib.???/nltk/_ctoken.so", where the name of the "lib.???" 
 * subdirectory depends on your architecture.  Copy this file to
 * "nltk/_ctoken.so", and you should be able to import the module with:
 *     >>> import nltk._ctoken
 */

#include <Python.h>
/*==================================================================
 * START LOCATION DEFINITION 
 *=================================================================*/

/*
OPERATIONS SUPPORTED:
    - Location.start()
    - Location.end()
    - Location.length()
    - Location.source()
    - Location.unit()
    - Location.__new__()
    - Location.__del__()
    - Location.__repr__()
    - Location.__cmp__()
    - Location.__hash__()
*/

/*
 STILL LEFT TO DO:
    - Location.start_loc
    - Location.end_loc
    - Locaiton.select
    - Location.union
    - Location.prec
    - Location.succ
    - Location.overlaps
    - Location.__str__
    - Location.__len__
    - Location.__add__
    - Location.__eq__ (for speed) [?]
    - others?
*/

/*-------------------------------------------------------
 * Location Type Declaration
 *-------------------------------------------------------*/
staticforward PyTypeObject locationType;

/* A macro to test if something's a Location. */
#define is_location(v) ((v)->ob_type == &locationType)

/*-------------------------------------------------------
 * Location Objects
 *-------------------------------------------------------*/

/* The struct that is used to encode Location instances. */
typedef struct {
    /* Object head: refcount & type */
    PyObject_HEAD

    /* The start index */
    long int start;

    /* The end index */
    long int end;

    /* The unit (use NULL for None) */
    char *unit;

    /* The source */
    PyObject *source;
} locationObject;

/*-------------------------------------------------------
 * Location Constructor/destructor
 *-------------------------------------------------------*/

/* The Location constructor */
static PyObject*
new_location(PyObject* self, PyObject *args, PyObject *keywords)
{
    PyObject *start = NULL;
    PyObject *end = NULL;
    PyObject *source = NULL;
    char *unit = NULL;
    static char *kwlist[] = {"start", "end", "unit", "source", NULL};
    
    /* Parse the arguments. */
    if (!PyArg_ParseTupleAndKeywords(args, keywords, "O|OsO:Location",
                                     kwlist, &start, &end, &unit, &source))
        return NULL;

    /* If source == NULL, then it defaults to None */
    if (source == NULL) {
        source = Py_None;
        Py_INCREF(Py_None);
    }

    /* Downcase the unit */
    if (unit != NULL) {
        char *c;
        for (c=unit; (*c)!=0; c++) (*c)=tolower(*c);
    }

    /* Integer-based locations */
    if (PyInt_Check(start)) {
        long int loc_start, loc_end;
        locationObject* loc;

        /* Set the start & end indices */
        loc_start = PyInt_AS_LONG(start);
        if ((end == NULL) || (end == Py_None))
            loc_end = loc_start + 1;
        else 
            loc_end = PyInt_AsLong(end); // does this raise TypeError?

        /* Check that start >= end */
        if (loc_end < loc_start) {
            PyErr_SetString(PyExc_ValueError, "A location's start index must be less than or equal to its end index.");
            return NULL;
        }

        /* Create & return a new location object. */
        loc = PyObject_New(locationObject, &locationType);
        loc->start = loc_start;
        loc->end = loc_end;
        loc->unit = unit;
        loc->source = source;
        return (PyObject*)loc;
    }

    /* Other index types for locations? */
    PyErr_SetString(PyExc_TypeError,
                    "Location() argument 2 must be an int (for now)");
    return NULL;
}

/* The location deallocator */
static void
location_dealloc(PyObject* self)
{
    PyObject_Del(self);
}

/*-------------------------------------------------------
 * Location Methods
 *-------------------------------------------------------*/

/* Location.start() */
static PyObject *location_start(locationObject* self, PyObject *args)
{
    if (!PyArg_ParseTuple(args,":Location.start")) 
        return NULL;

    return PyInt_FromLong(self->start);
}

/* Location.end() */
static PyObject *location_end(locationObject* self, PyObject *args)
{
    if (!PyArg_ParseTuple(args,":Location.end")) 
        return NULL;

    return PyInt_FromLong(self->end);
}

/* Location.length() */
static PyObject *location_length(locationObject* self, PyObject *args)
{
    if (!PyArg_ParseTuple(args,":Location.length")) 
        return NULL;

    return PyInt_FromLong(self->end - self->start);
}

/* Location.source() */
static PyObject *location_source(locationObject* self, PyObject *args)
{
    if (!PyArg_ParseTuple(args,":Location.source")) 
        return NULL;

    Py_INCREF(self->source);
    return self->source;
}

/* Location.unit() */
static PyObject *location_unit(locationObject* self, PyObject *args)
{
    if (!PyArg_ParseTuple(args,":Location.unit")) 
        return NULL;

    if (self->unit == NULL)
    {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else
        return PyString_FromString(self->unit);
}

/* Location methods */
static PyMethodDef location_methods[] = {
    /* Location.start() */
    {"start", (PyCFunction)location_start, METH_VARARGS,
     "Return the start index of this Location."},
    
    /* Location.end() */
    {"end", (PyCFunction)location_end, METH_VARARGS,
     "Return the end index of this Location."},

    /* Location.length() */
    {"length", (PyCFunction)location_length, METH_VARARGS,
     "Return the length of this Location."},

    /* Location.source() */
    {"source", (PyCFunction)location_source, METH_VARARGS,
     "Return the source of this Location."},

    /* Location.unit() */
    {"unit", (PyCFunction)location_unit, METH_VARARGS,
     "Return the unit of this Location."},

    /* End of list */
    {NULL, NULL, 0, NULL}
};

/* The getattr() operator, which retrieves methods. */
static PyObject *location_getattr(locationObject *loc, char *name)
{
    return Py_FindMethod(location_methods, (PyObject *)loc, name);
}

/*-------------------------------------------------------
 * Location Operators
 *-------------------------------------------------------*/

static int check_units_and_source(locationObject *loc1, locationObject *loc2)
{
    /* Check that the units match */
    if (loc1->unit == NULL || loc2->unit == NULL)
    {
        if (!(loc1->unit == NULL) || !(loc2->unit == NULL))
        {
            PyErr_SetString(PyExc_ValueError,
                            "Locations have incompatible units");
            return 0;
        }
    }
    else if (strcmp(loc1->unit, loc2->unit) != 0)
    {
        PyErr_SetString(PyExc_ValueError,
                        "Locations have incompatible units");
        return 0;
    }

    /* Check that the sources match */
    if (loc1->source != loc2->source)
    {
        PyErr_SetString(PyExc_ValueError,
                        "Locations have incompatible sources");
        return 0;
    }

    return 1;
}

/* The location repr() operator */
static PyObject *location_repr(locationObject *loc)
{
    if (loc->end == loc->start+1) {
        if (loc->unit == NULL)
            return PyString_FromFormat("@[%ld]", loc->start);
        else
            return PyString_FromFormat("@[%ld%s]", loc->start, loc->unit);
    }
    else if (loc->unit == NULL) 
        return PyString_FromFormat("@[%ld:%ld]", loc->start, loc->end);
    else
        return PyString_FromFormat("@[%ld%s:%ld%s]", loc->start, loc->unit,
                                   loc->end, loc->unit);
}

/* The location cmp() operator */
static int location_compare(locationObject *loc1, locationObject *loc2)
{
    /* Make sure loc2 is a location */
    if (!is_location(loc2))
        return -1;

    /* Check for unit/source mismatches */
    if (!check_units_and_source(loc1, loc2))
        return -1;

    /* Compare the start & end indices. */
    if (loc1->start < loc2->start)
        return -1;
    else if (loc1->start > loc2->start)
        return 1;
    else if (loc1->end < loc2->end)
        return -1;
    else if (loc1->end > loc2->end)
        return 1;
    else
        return 0;
}
            
static long location_hash(locationObject *loc)
{
    /* It's unusual for 2 locations to share a start location; so just
     * hash off the start location. */
    return loc->start;
}

/*-------------------------------------------------------
 * Location Type Definition
 *-------------------------------------------------------*/ 

static PyTypeObject locationType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "Location", /* Name (for printing the type itself) */
    sizeof(locationObject), 0, /* Size */
    location_dealloc, /*tp_dealloc*/
    0, /*tp_print*/
    (getattrfunc)location_getattr, /*tp_getattr*/
    0, /*tp_setattr*/
    (cmpfunc)location_compare, /*tp_compare*/
    (reprfunc)location_repr, /*tp_repr*/
    0, /*tp_as_number*/
    0, /*tp_as_sequence*/
    0, /*tp_as_mapping*/
    (hashfunc)location_hash, /*tp_hash */
    0, /* tp_call */
    0, /* tp_str */
    0, /* tp_getattro */
    0, /* tp_setattro */
    0, /* tp_as_buffer */
    0, /* tp_flags */
    "A span over indices in text." /* tp_doc */
};

/*==================================================================
 * START TOKEN DEFINITION 
 *=================================================================*/

/*-------------------------------------------------------
 * Token Type Declaration
 *-------------------------------------------------------*/
staticforward PyTypeObject tokenType;

/* A macro to test if something's a Token. */
#define is_token(v) ((v)->ob_type == &tokenType)

/*-------------------------------------------------------
 * Token Objects
 *-------------------------------------------------------*/

/* The struct that is used to encode Token instances. */
typedef struct {
    /* Object head: refcount & type */
    PyObject_HEAD

    /* The token's type */
    PyObject *type;

    /* The token's location */
    PyObject *loc;
} tokenObject;

/*-------------------------------------------------------
 * Token Constructor/destructor
 *-------------------------------------------------------*/

/*-------------------------------------------------------
 * Token Methods
 *-------------------------------------------------------*/

/*-------------------------------------------------------
 * Token Operators
 *-------------------------------------------------------*/

/*-------------------------------------------------------
 * Token Type Definition
 *-------------------------------------------------------*/ 

static PyTypeObject tokenType = {
    PyObject_HEAD_INIT(NULL)
    0,
    "Token", /* Name (for printing the type itself) */
    sizeof(tokenObject), 0, /* Size */
    0, /*tp_dealloc*/
    0, /*tp_print*/
    0, /*tp_getattr*/
    0, /*tp_setattr*/
    0, /*tp_compare*/
    0, /*tp_repr*/
    0, /*tp_as_number*/
    0, /*tp_as_sequence*/
    0, /*tp_as_mapping*/
    0, /*tp_hash */
    0, /* tp_call */
    0, /* tp_str */
    0, /* tp_getattro */
    0, /* tp_setattro */
    0, /* tp_as_buffer */
    0, /* tp_flags */
    "A token." /* tp_doc */
};


/*==================================================================
 * START MODULE DEFINITION
 *=================================================================*/

/* Methods defined by the token module. */
static PyMethodDef _ctoken_methods[] = {
    /* The Location constructor function. */
    {"new_location", (PyCFunction)new_location,
     METH_VARARGS|METH_KEYWORDS,
     "Create a new Location object."},

    /* End of list */
    {NULL, NULL, 0, NULL}
};

/* Module initializer */
DL_EXPORT(void) init_ctoken(void) 
{
    PyObject *d, *m;
    
    /* type(Location) = <type 'type'> */
    locationType.ob_type = &PyType_Type;

    /* This lets the type itself be used as a constructor (rather than
     * having to use new_location to create locations).  But it's only
     * possible in Python 2.2+ */
#if PY_MAJOR_VERSION >= 2 && PY_MINOR_VERSION >= 2
    locationType.tp_new = (newfunc)new_location;
#endif

    /* Initialize the module */
    m = Py_InitModule("_ctoken", _ctoken_methods);

    /* Add the type */
    d = PyModule_GetDict(m);
    PyDict_SetItemString(d, "location_type", (PyObject*)&locationType);

}

//from nltk._ctoken import *
