/* Natural Language Toolkit: C Implementation of Locations
 *
 * Copyright (C) 2003 University of Pennsylvania
 * Author: Edward Loper <edloper@gradient.cis.upenn.edu>
 * URL: <http://nltk.sourceforge.net>
 * For license information, see LICENSE.TXT
 *
 * $Id$
 *
 * This class provides a drop-in replacement for the Location class.
 * Since Locations are used extensively in NLTK (for Tokens), this C
 * implementation can give a signifigant performance boost. 
 */

#include <Python.h>
#include "location_object.h"

/*************************************************************
 STILL LEFT TO DO:
    - Location.start_loc
    - Location.end_loc
    - Locaiton.select
    - Location.union
    - Location.prec
    - Location.succ
    - Location.overlaps
    - Location.__len__
    - Location.__add__
    - Location.__eq__ (for speed) [?]
    - others?
*************************************************************/

/*=================================================================
 * Location Object
 *=================================================================*/

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

/*=================================================================
 * Location Constructor/destructor
 *=================================================================*/

/* The Location constructor */
PyObject*
create_location(PyObject* self, PyObject *args, PyObject *keywords)
{
    /* Parse the arguments. */
    static char *kwlist[] = {"start", "end", "unit", "source", NULL};
    
    /* Initialize the new location object. */
    locationObject* loc;
    loc = PyObject_New(locationObject, &locationType);
    loc->end = -1;
    loc->unit = NULL;
    loc->source = Py_None; /* ref count?? */

    if (!PyArg_ParseTupleAndKeywords(args, keywords, "l|lsO:Location",
                                     kwlist, &(loc->start), &(loc->end),
                                     &(loc->unit), &(loc->source)))
        return NULL;

    /* If end wasn't specified, then set it. */
    if (loc->end == -1)
        loc->end = loc->start+1;

    /* Return the location object. */
    return (PyObject*)loc;
}

/* The location deallocator */
static void
location_dealloc(PyObject* self)
{
    PyObject_Del(self);
}

/*=================================================================
 * Location Methods
 *=================================================================*/

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

/*=================================================================
 * Location Operators
 *=================================================================*/

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
    return PyString_FromFormat("@[%ld:%ld]", loc->start, loc->end);
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

/*=================================================================
 * Location Type Definition
 *=================================================================*/

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

