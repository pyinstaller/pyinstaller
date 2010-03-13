
/* -*- C -*- */
/*
 *  block_template.c : Generic framework for block encryption algorithms
 *
 * Distribute and use freely; there are no restrictions on further 
 * dissemination and usage except those imposed by the laws of your 
 * country of residence.  This software is provided "as is" without
 * warranty of fitness for use or suitability for any purpose, express
 * or implied. Use at your own risk or not at all. 
 *
 */


#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#ifdef _HAVE_STDC_HEADERS
#include <string.h>
#endif

#include "Python.h"
#include "modsupport.h" 

/* Cipher operation modes */

#define MODE_ECB 1
#define MODE_CBC 2
#define MODE_CFB 3
#define MODE_PGP 4
#define MODE_OFB 5
#define MODE_CTR 6

#define _STR(x) #x
#define _XSTR(x) _STR(x)
#define _PASTE(x,y) x##y
#define _PASTE2(x,y) _PASTE(x,y)
#define _MODULE_NAME _PASTE2(init,MODULE_NAME)
#define _MODULE_STRING _XSTR(MODULE_NAME)

typedef struct 
{
	PyObject_HEAD 
	int mode, count, segment_size;
	unsigned char IV[BLOCK_SIZE], oldCipher[BLOCK_SIZE];
	PyObject *counter;
	block_state st;
} ALGobject;

staticforward PyTypeObject ALGtype;

#define is_ALGobject(v)		((v)->ob_type == &ALGtype)

static ALGobject *
newALGobject(void)
{
	ALGobject * new;
	new = PyObject_New(ALGobject, &ALGtype);
	new->mode = MODE_ECB;
	new->counter = NULL;
	return new;
}

static void
ALGdealloc(PyObject *ptr)
{		
	ALGobject *self = (ALGobject *)ptr;

	/* Overwrite the contents of the object */
	Py_XDECREF(self->counter);
	self->counter = NULL;
	memset(self->IV, 0, BLOCK_SIZE);
	memset(self->oldCipher, 0, BLOCK_SIZE);
	memset((char*)&(self->st), 0, sizeof(block_state));
	self->mode = self->count = self->segment_size = 0;
	PyObject_Del(ptr);
}


static char ALGnew__doc__[] = 
"new(key, [mode], [IV]): Return a new " _MODULE_STRING " encryption object.";

static char *kwlist[] = {"key", "mode", "IV", "counter", "segment_size",
#ifdef PCT_RC5_MODULE
			 "version", "word_size", "rounds",
#endif
			 NULL};

static ALGobject *
ALGnew(PyObject *self, PyObject *args, PyObject *kwdict)
{
	unsigned char *key, *IV;
	ALGobject * new=NULL;
	int keylen, IVlen=0, mode=MODE_ECB, segment_size=0;
	PyObject *counter = NULL;
#ifdef PCT_RC5_MODULE
	int version = 0x10, word_size = 32, rounds = 16; /*XXX default rounds? */
#endif 
	/* Set default values */
	if (!PyArg_ParseTupleAndKeywords(args, kwdict, "s#|is#Oi"
#ifdef PCT_RC5_MODULE
					 "iii"
#endif 
					 , kwlist,
					 &key, &keylen, &mode, &IV, &IVlen,
					 &counter, &segment_size
#ifdef PCT_RC5_MODULE
					 , &version, &word_size, &rounds
#endif
		)) 
	{
		return NULL;
	}

	if (KEY_SIZE!=0 && keylen!=KEY_SIZE)
	{
		PyErr_Format(PyExc_ValueError, 
			     "Key must be %i bytes long, not %i",
			     KEY_SIZE, keylen);
		return NULL;
	}
	if (KEY_SIZE==0 && keylen==0)
	{
		PyErr_SetString(PyExc_ValueError, 
				"Key cannot be the null string");
		return NULL;
	}
	if (IVlen != BLOCK_SIZE && IVlen != 0)
	{
		PyErr_Format(PyExc_ValueError, 
			     "IV must be %i bytes long", BLOCK_SIZE);
		return NULL;
	}
	if (mode<MODE_ECB || mode>MODE_CTR) 
	{
		PyErr_Format(PyExc_ValueError, 
			     "Unknown cipher feedback mode %i",
			     mode);
		return NULL;
	}

	/* Mode-specific checks */
	if (mode == MODE_CFB) {
		if (segment_size == 0) segment_size = 8;
		if (segment_size < 1 || segment_size > BLOCK_SIZE*8) {
			PyErr_Format(PyExc_ValueError, 
				     "segment_size must be multiple of 8 "
				     "between 1 and %i", BLOCK_SIZE);
		}
	}

	if (mode == MODE_CTR) {
		if (!PyCallable_Check(counter)) {
			PyErr_SetString(PyExc_ValueError, 
					"'counter' parameter must be a callable object");
		}
	} else {
		if (counter != NULL) {
			PyErr_SetString(PyExc_ValueError, 
					"'counter' parameter only useful with CTR mode");
		}
	}

	/* Cipher-specific checks */
#ifdef PCT_RC5_MODULE
	if (version!=0x10) {
		PyErr_Format(PyExc_ValueError,
			     "RC5: Bad RC5 algorithm version: %i",
			     version);
		return NULL;
	}
	if (word_size!=16 && word_size!=32) {
		PyErr_Format(PyExc_ValueError,
			     "RC5: Unsupported word size: %i",
			     word_size);
		return NULL;
	}
	if (rounds<0 || 255<rounds) {
		PyErr_Format(PyExc_ValueError,
			     "RC5: rounds must be between 0 and 255, not %i",
			     rounds);
		return NULL;
	}
#endif

	/* Copy parameters into object */
	new = newALGobject();
	new->segment_size = segment_size;
	new->counter = counter;
	Py_XINCREF(counter);
#ifdef PCT_RC5_MODULE
	new->st.version = version;
	new->st.word_size = word_size;
	new->st.rounds = rounds;
#endif

	block_init(&(new->st), key, keylen);
	if (PyErr_Occurred())
	{
		Py_DECREF(new);
		return NULL;
	}
	memset(new->IV, 0, BLOCK_SIZE);
	memset(new->oldCipher, 0, BLOCK_SIZE);
	memcpy(new->IV, IV, IVlen);
	new->mode = mode;
	new->count=8;
	return new;
}

static char ALG_Encrypt__doc__[] =
"Encrypt the provided string of binary data.";

static PyObject *
ALG_Encrypt(ALGobject *self, PyObject *args)
{
	unsigned char *buffer, *str;
	unsigned char temp[BLOCK_SIZE];
	int i, j, len;
	PyObject *result;
  
	if (!PyArg_Parse(args, "s#", &str, &len))
		return NULL;
	if (len==0)			/* Handle empty string */
	{
		return PyString_FromStringAndSize(NULL, 0);
	}
	if ( (len % BLOCK_SIZE) !=0 && 
	     (self->mode!=MODE_CFB) && (self->mode!=MODE_PGP))
	{
		PyErr_Format(PyExc_ValueError, 
			     "Input strings must be "
			     "a multiple of %i in length",
			     BLOCK_SIZE);
		return NULL;
	}
	if (self->mode == MODE_CFB && 
	    (len % (self->segment_size/8) !=0)) {
		PyErr_Format(PyExc_ValueError, 
			     "Input strings must be a multiple of "
			     "the segment size %i in length",
			     self->segment_size/8);
		return NULL;
	}

	buffer=malloc(len);
	if (buffer==NULL) 
	{
		PyErr_SetString(PyExc_MemoryError, 
				"No memory available in "
				_MODULE_STRING " encrypt");
		return NULL;
	}
	switch(self->mode)
	{
	case(MODE_ECB):      
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			block_encrypt(&(self->st), str+i, buffer+i);
		}
		break;

	case(MODE_CBC):      
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			for(j=0; j<BLOCK_SIZE; j++)
			{
				temp[j]=str[i+j]^self->IV[j];
			}
			block_encrypt(&(self->st), temp, buffer+i);
			memcpy(self->IV, buffer+i, BLOCK_SIZE);
		}
		break;

	case(MODE_CFB):      
		for(i=0; i<len; i+=self->segment_size/8) 
		{
			block_encrypt(&(self->st), self->IV, temp);
			for (j=0; j<self->segment_size/8; j++) {
				buffer[i+j] = str[i+j] ^ temp[j];
			}
			if (self->segment_size == BLOCK_SIZE * 8) {
				/* s == b: segment size is identical to 
				   the algorithm block size */
				memcpy(self->IV, buffer + i, BLOCK_SIZE);
			}
			else if ((self->segment_size % 8) == 0) {
				int sz = self->segment_size/8;
				memmove(self->IV, self->IV + sz, 
					BLOCK_SIZE-sz);
				memcpy(self->IV + BLOCK_SIZE - sz, buffer + i,
				       sz);
			}
			else {
				/* segment_size is not a multiple of 8; 
				   currently this can't happen */
			}
		}
		break;

	case(MODE_PGP):
		if (len<=BLOCK_SIZE-self->count) 
		{			
			/* If less than one block, XOR it in */
			for(i=0; i<len; i++) 
				buffer[i] = self->IV[self->count+i] ^= str[i];
			self->count += len;
		}
		else 
		{
			int j;
			for(i=0; i<BLOCK_SIZE-self->count; i++) 
				buffer[i] = self->IV[self->count+i] ^= str[i];
			self->count=0;
			for(; i<len-BLOCK_SIZE; i+=BLOCK_SIZE) 
			{
				block_encrypt(&(self->st), self->oldCipher, 
					      self->IV);
				for(j=0; j<BLOCK_SIZE; j++)
					buffer[i+j] = self->IV[j] ^= str[i+j];
			}
			/* Do the remaining 1 to BLOCK_SIZE bytes */
			block_encrypt(&(self->st), self->oldCipher, self->IV);
			self->count=len-i;
			for(j=0; j<len-i; j++) 
			{
				buffer[i+j] = self->IV[j] ^= str[i+j];
			}
		}
		break;

	case(MODE_OFB):
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			block_encrypt(&(self->st), self->IV, temp);
			memcpy(self->IV, temp, BLOCK_SIZE);
			for(j=0; j<BLOCK_SIZE; j++)
			{
				buffer[i+j] = str[i+j] ^ temp[j];
			}
		}      
		break;

	case(MODE_CTR):
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			PyObject *ctr = PyObject_CallObject(self->counter, NULL);
			if (ctr == NULL) {
				free(buffer);
				return NULL;
			}
			if (!PyString_Check(ctr))
			{
				PyErr_SetString(PyExc_TypeError, 
						"CTR counter function didn't return a string");
				Py_DECREF(ctr);
				free(buffer);
				return NULL;
			}
			if (PyString_Size(ctr) != BLOCK_SIZE) {
				PyErr_Format(PyExc_TypeError, 
					     "CTR counter function returned "
					     "string not of length %i",
					     BLOCK_SIZE);
				Py_DECREF(ctr);
				free(buffer);
				return NULL;
			}
			block_encrypt(&(self->st), PyString_AsString(ctr), 
				      temp);
			Py_DECREF(ctr);
			for(j=0; j<BLOCK_SIZE; j++)
			{
				buffer[i+j] = str[i+j]^temp[j];
			}
		}
		break;

	default:
		PyErr_Format(PyExc_SystemError, 
			     "Unknown ciphertext feedback mode %i; "
			     "this shouldn't happen",
			     self->mode);
		free(buffer);
		return NULL;
	}
	result=PyString_FromStringAndSize(buffer, len);
	free(buffer);
	return(result);
}

static char ALG_Decrypt__doc__[] =
"decrypt(string): Decrypt the provided string of binary data.";


static PyObject *
ALG_Decrypt(ALGobject *self, PyObject *args)
{
	unsigned char *buffer, *str;
	unsigned char temp[BLOCK_SIZE];
	int i, j, len;
	PyObject *result;
  
	if (!PyArg_Parse(args, "s#", &str, &len))
		return NULL;
	if (len==0)			/* Handle empty string */
	{
		return PyString_FromStringAndSize(NULL, 0);
	}
	if ( (len % BLOCK_SIZE) !=0 && 
	     (self->mode!=MODE_CFB && self->mode!=MODE_PGP))
	{
		PyErr_Format(PyExc_ValueError, 
			     "Input strings must be "
			     "a multiple of %i in length",
			     BLOCK_SIZE);
		return NULL;
	}
	if (self->mode == MODE_CFB && 
	    (len % (self->segment_size/8) !=0)) {
		PyErr_Format(PyExc_ValueError, 
			     "Input strings must be a multiple of "
			     "the segment size %i in length",
			     self->segment_size/8);
		return NULL;
	}
	buffer=malloc(len);
	if (buffer==NULL) 
	{
		PyErr_SetString(PyExc_MemoryError, 
				"No memory available in " _MODULE_STRING
				" decrypt");
		return NULL;
	}
	switch(self->mode)
	{
	case(MODE_ECB):      
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			block_decrypt(&(self->st), str+i, buffer+i);
		}
		break;

	case(MODE_CBC):      
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			memcpy(self->oldCipher, self->IV, BLOCK_SIZE);
			block_decrypt(&(self->st), str+i, temp);
			for(j=0; j<BLOCK_SIZE; j++) 
			{
				buffer[i+j]=temp[j]^self->IV[j];
				self->IV[j]=str[i+j];
			}
		}
		break;

	case(MODE_CFB):      
		for(i=0; i<len; i+=self->segment_size/8) 
		{
			block_encrypt(&(self->st), self->IV, temp);
			for (j=0; j<self->segment_size/8; j++) {
				buffer[i+j] = str[i+j]^temp[j];
			}
			if (self->segment_size == BLOCK_SIZE * 8) {
				/* s == b: segment size is identical to 
				   the algorithm block size */
				memcpy(self->IV, str + i, BLOCK_SIZE);
			}
			else if ((self->segment_size % 8) == 0) {
				int sz = self->segment_size/8;
				memmove(self->IV, self->IV + sz, 
					BLOCK_SIZE-sz);
				memcpy(self->IV + BLOCK_SIZE - sz, str + i, 
				       sz);
			}
			else {
				/* segment_size is not a multiple of 8; 
				   currently this can't happen */
			}
		}
		break;

	case(MODE_PGP):
		if (len<=BLOCK_SIZE-self->count) 
		{			
                        /* If less than one block, XOR it in */
			unsigned char t;
			for(i=0; i<len; i++)
			{
				t=self->IV[self->count+i];
				buffer[i] = t ^ (self->IV[self->count+i] = str[i]);
			}
			self->count += len;
		}
		else 
		{
			int j;
			unsigned char t;
			for(i=0; i<BLOCK_SIZE-self->count; i++) 
			{
				t=self->IV[self->count+i];
				buffer[i] = t ^ (self->IV[self->count+i] = str[i]);
			}
			self->count=0;
			for(; i<len-BLOCK_SIZE; i+=BLOCK_SIZE) 
			{
				block_encrypt(&(self->st), self->oldCipher, self->IV);
				for(j=0; j<BLOCK_SIZE; j++)
				{
					t=self->IV[j];
					buffer[i+j] = t ^ (self->IV[j] = str[i+j]);
				}
			}
			/* Do the remaining 1 to BLOCK_SIZE bytes */
			block_encrypt(&(self->st), self->oldCipher, self->IV);
			self->count=len-i;
			for(j=0; j<len-i; j++) 
			{
				t=self->IV[j];
				buffer[i+j] = t ^ (self->IV[j] = str[i+j]);
			}
		}
		break;

	case (MODE_OFB):
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			block_encrypt(&(self->st), self->IV, temp);
			memcpy(self->IV, temp, BLOCK_SIZE);
			for(j=0; j<BLOCK_SIZE; j++)
			{
				buffer[i+j] = str[i+j] ^ self->IV[j];
			}
		}      
		break;

	case (MODE_CTR):
		for(i=0; i<len; i+=BLOCK_SIZE) 
		{
			PyObject *ctr = PyObject_CallObject(self->counter, NULL);
			if (ctr == NULL) {
				free(buffer);
				return NULL;
			}
			if (!PyString_Check(ctr))
			{
				PyErr_SetString(PyExc_TypeError, 
						"CTR counter function didn't return a string");
				Py_DECREF(ctr);
				free(buffer);
				return NULL;
			}
			if (PyString_Size(ctr) != BLOCK_SIZE) {
				PyErr_SetString(PyExc_TypeError, 
						"CTR counter function returned string of incorrect length");
				Py_DECREF(ctr);
				free(buffer);
				return NULL;
			}
			block_encrypt(&(self->st), PyString_AsString(ctr), temp);
			Py_DECREF(ctr);
			for(j=0; j<BLOCK_SIZE; j++)
			{
				buffer[i+j] = str[i+j]^temp[j];
			}
		}
		break;

	default:
		PyErr_Format(PyExc_SystemError, 
			     "Unknown ciphertext feedback mode %i; "
			     "this shouldn't happen",
			     self->mode);
		free(buffer);
		return NULL;
	}
	result=PyString_FromStringAndSize(buffer, len);
	free(buffer);
	return(result);
}

static char ALG_Sync__doc__[] =
"sync(): For objects using the PGP feedback mode, this method modifies "
"the IV, synchronizing it with the preceding ciphertext.";

static PyObject *
ALG_Sync(ALGobject *self, PyObject *args)
{
	if (!PyArg_ParseTuple(args, "")) {
		return NULL;
	}

	if (self->mode!=MODE_PGP) 
	{
		PyErr_SetString(PyExc_SystemError, "sync() operation not defined for "
				"this feedback mode");
		return NULL;
	}
	
	if (self->count!=8) 
	{
		memmove(self->IV+BLOCK_SIZE-self->count, self->IV, 
			self->count);
		memcpy(self->IV, self->oldCipher+self->count, 
		       BLOCK_SIZE-self->count);
		self->count=8;
	}
	Py_INCREF(Py_None);
	return Py_None;
}

#if 0
void PrintState(self, msg)
     ALGobject *self;
     char * msg;
{
  int count;
  
  printf("%sing: %i IV ", msg, (int)self->count);
  for(count=0; count<8; count++) printf("%i ", self->IV[count]);
  printf("\noldCipher:");
  for(count=0; count<8; count++) printf("%i ", self->oldCipher[count]);
  printf("\n");
}
#endif


/* ALG object methods */

static PyMethodDef ALGmethods[] =
{
 {"encrypt", (PyCFunction) ALG_Encrypt, 0, ALG_Encrypt__doc__},
 {"decrypt", (PyCFunction) ALG_Decrypt, 0, ALG_Decrypt__doc__},
 {"sync", (PyCFunction) ALG_Sync, METH_VARARGS, ALG_Sync__doc__},
 {NULL, NULL}			/* sentinel */
};


static int
ALGsetattr(PyObject *ptr, char *name, PyObject *v)
{
  ALGobject *self=(ALGobject *)ptr;
  if (strcmp(name, "IV") != 0) 
    {
      PyErr_Format(PyExc_AttributeError,
		   "non-existent block cipher object attribute '%s'",
		   name);
      return -1;
    }
  if (v==NULL)
    {
      PyErr_SetString(PyExc_AttributeError,
		      "Can't delete IV attribute of block cipher object");
      return -1;
    }
  if (!PyString_Check(v))
    {
      PyErr_SetString(PyExc_TypeError,
		      "IV attribute of block cipher object must be string");
      return -1;
    }
  if (PyString_Size(v)!=BLOCK_SIZE) 
    {
      PyErr_Format(PyExc_ValueError, 
		   _MODULE_STRING " IV must be %i bytes long",
		   BLOCK_SIZE);
      return -1;
    }
  memcpy(self->IV, PyString_AsString(v), BLOCK_SIZE);
  return 0;
}

static PyObject *
ALGgetattr(PyObject *s, char *name)
{
  ALGobject *self = (ALGobject*)s;
  if (strcmp(name, "IV") == 0) 
    {
      return(PyString_FromStringAndSize(self->IV, BLOCK_SIZE));
    }
  if (strcmp(name, "mode") == 0)
     {
       return(PyInt_FromLong((long)(self->mode)));
     }
  if (strcmp(name, "block_size") == 0)
     {
       return PyInt_FromLong(BLOCK_SIZE);
     }
  if (strcmp(name, "key_size") == 0)
     {
       return PyInt_FromLong(KEY_SIZE);
     }
 return Py_FindMethod(ALGmethods, (PyObject *) self, name);
}

/* List of functions defined in the module */

static struct PyMethodDef modulemethods[] =
{
 {"new", (PyCFunction) ALGnew, METH_VARARGS|METH_KEYWORDS, ALGnew__doc__},
 {NULL, NULL}			/* sentinel */
};

static PyTypeObject ALGtype =
{
	PyObject_HEAD_INIT(NULL)
	0,				/*ob_size*/
	_MODULE_STRING,		/*tp_name*/
	sizeof(ALGobject),	/*tp_size*/
	0,				/*tp_itemsize*/
	/* methods */
	ALGdealloc,	/*tp_dealloc*/
	0,				/*tp_print*/
	ALGgetattr,	/*tp_getattr*/
	ALGsetattr,    /*tp_setattr*/
	0,			/*tp_compare*/
	(reprfunc) 0,			/*tp_repr*/
	0,				/*tp_as_number*/
};

/* Initialization function for the module */

#if PYTHON_API_VERSION < 1011
#define PyModule_AddIntConstant(m,n,v) {PyObject *o=PyInt_FromLong(v); \
           if (o!=NULL) \
             {PyDict_SetItemString(PyModule_GetDict(m),n,o); Py_DECREF(o);}}
#endif

void
_MODULE_NAME (void)
{
	PyObject *m;

	ALGtype.ob_type = &PyType_Type;

	/* Create the module and add the functions */
	m = Py_InitModule(_MODULE_STRING, modulemethods);

	PyModule_AddIntConstant(m, "MODE_ECB", MODE_ECB);
	PyModule_AddIntConstant(m, "MODE_CBC", MODE_CBC);
	PyModule_AddIntConstant(m, "MODE_CFB", MODE_CFB);
	PyModule_AddIntConstant(m, "MODE_PGP", MODE_PGP);
	PyModule_AddIntConstant(m, "MODE_OFB", MODE_OFB);
	PyModule_AddIntConstant(m, "MODE_CTR", MODE_CTR);
	PyModule_AddIntConstant(m, "block_size", BLOCK_SIZE);
	PyModule_AddIntConstant(m, "key_size", KEY_SIZE);

	/* Check for errors */
	if (PyErr_Occurred())
		Py_FatalError("can't initialize module " _MODULE_STRING);
}

