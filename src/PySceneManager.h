/**
 * \file   
 * \brief      PySceneManager class declaration.
 * \author     Thomas Moeller
 * \details
 *
 * Copyright (C) the PyInventor contributors. All rights reserved.
 * This file is part of PyInventor, distributed under the BSD 3-Clause
 * License. For full terms see the included COPYING file.
 */


#pragma once

#include "PySceneObject.h"
#include <Inventor/nodes/SoCamera.h>

class SoSceneManager;
class SoSeparator;
class SbSphereSheetProjector;
class SoEvent;

// for VSG Inventor use of context class is required
class SoGLContext;


class PySceneManager
{
public:
	static PyTypeObject *getType();
	static bool getScene(PyObject* self, PyObject *&scene_out, int &viewportWidth_out, int &viewportHeight_out, SbColor &backgroundColor_out, SoSeparator **backgroundScene_out = 0);
	static SbBool getBackgroundFromObject(PyObject *object, SbColor &color_out, SoSeparator **scene_inout);

private:
	typedef struct 
	{
		PyObject_HEAD
		SoSceneManager *sceneManager;
		SbSphereSheetProjector *sphereSheetProjector;
		SoSeparator *gradientBackground;
		PyObject *scene;
		PyObject *renderCallback;
		PyObject *backgroundColor;
		SoGLContext *context;
		enum ManipulationMode {
			SCENE,
			CAMERA
		} manipMode;
		bool isManipulating;
	} Object;

	// type implementations
	static void tp_dealloc(Object *self);
	static PyObject* tp_new(PyTypeObject *type, PyObject *args, PyObject *kwds);
	static int tp_init(Object *self, PyObject *args, PyObject *kwds);
	static int tp_setattro(Object* self, PyObject *attrname, PyObject *value);

	// methods
    static PyObject* init_gl(Object *self, PyObject *args);
    static PyObject* render(Object *self, PyObject *args);
	static PyObject* resize(Object *self, PyObject *args);
	static PyObject* mouse_button(Object *self, PyObject *args);
	static PyObject* mouse_move(Object *self, PyObject *args);
    static PyObject* motion3(Object *self, PyObject *args);
	static PyObject* key(Object *self, PyObject *args);
	static PyObject* view_all(Object *self, PyObject *args);
	static PyObject* interaction(Object *self, PyObject *args);
    static PyObject* is_grabbing(Object *self);
    static PyObject* release_grabber(Object *self);

	// internal
	static void renderCBFunc(void *userdata, SoSceneManager *mgr);
	static void processEvent(Object *self, SoEvent *e);
	static SoCamera *getCamera(Object *self);
	static void rotateCamera(SoCamera *camera, SbRotation orient);
};

