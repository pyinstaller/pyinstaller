#include "Python.h"


static PyModuleDef mod_def = {
	PyModuleDef_HEAD_INIT,
	"package.pkgext",
	NULL,
	0,
	NULL,
	NULL,
	NULL,
	NULL,
	NULL
};

PyObject* PyInit_pkgext(void)
{
	return PyModule_Create(&mod_def);
}
