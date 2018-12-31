#include "Python.h"


static PyModuleDef mod_def = {
	PyModuleDef_HEAD_INIT,
	"extension",
	NULL,
	0,
	NULL,
	NULL,
	NULL,
	NULL,
	NULL
};

PyObject* PyInit_extension(void)
{
	return PyModule_Create(&mod_def);
}
