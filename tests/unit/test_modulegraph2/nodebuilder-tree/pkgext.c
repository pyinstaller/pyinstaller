#include "Python.h"


static PyModuleDef mod_def = {
	PyModuleDef_HEAD_INIT,
	"package.extmod",
	NULL,
	0,
	NULL,
	NULL,
	NULL,
	NULL,
	NULL
};

PyObject* PyInit_extmod(void)
{
	return PyModule_Create(&mod_def);
}
