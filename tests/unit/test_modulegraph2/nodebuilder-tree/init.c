#include "Python.h"


static PyModuleDef mod_def = {
	PyModuleDef_HEAD_INIT,
	"ext_package.__init__",
	NULL,
	0,
	NULL,
	NULL,
	NULL,
	NULL,
	NULL
};

#ifdef MS_WINDOWS
PyObject* PyInit___init__(void)
#else
PyObject* PyInit_ext_package(void)
#endif
{
	return PyModule_Create(&mod_def);
}
