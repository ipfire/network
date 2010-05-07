

#include <Python.h>

#include "isys.h"
#include "mount.h"


static PyObject * doMount(PyObject * s, PyObject * args);
static PyObject * doUMount(PyObject * s, PyObject * args);

static PyMethodDef isysModuleMethods[] = {
    { "mount", (PyCFunction) doMount, METH_VARARGS, NULL },
    { "umount", (PyCFunction) doUMount, METH_VARARGS, NULL },
};

void init_isys(void) {
    PyObject * m, * d;

    m = Py_InitModule("_isys", isysModuleMethods);
    d = PyModule_GetDict(m);
}

static PyObject * doMount(PyObject * s, PyObject * args) {
    char *err = NULL, *fs, *device, *mntpoint, *flags = NULL;
    int rc;

    if (!PyArg_ParseTuple(args, "sss|z", &fs, &device, &mntpoint,
			  &flags)) return NULL;

    rc = doPwMount(device, mntpoint, fs, flags, &err);
    if (rc == MOUNT_ERR_ERRNO)
        PyErr_SetFromErrno(PyExc_SystemError);
    else if (rc) {
        PyObject *tuple = PyTuple_New(2);

        PyTuple_SetItem(tuple, 0, PyInt_FromLong(rc));
        PyTuple_SetItem(tuple, 1, PyString_FromString(err));
        PyErr_SetObject(PyExc_SystemError, tuple);
    }

    if (rc)
        return NULL;

    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject * doUMount(PyObject * s, PyObject * args) {
    char * fs;

    if (!PyArg_ParseTuple(args, "s", &fs))
        return NULL;

    if (umount(fs)) {
	   PyErr_SetFromErrno(PyExc_SystemError);
	   return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}
