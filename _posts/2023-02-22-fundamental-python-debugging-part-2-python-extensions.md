---
title: "Fundamental Python Debugging Part 2 - Python Extensions"
date: 2023-02-22T00:00:00
description: This blog post teaches you how to debug C extensions to Python. It is part 2 of a 3 part series.
categories:
  - debugging
tags:
  - python
  - c
# cSpell:ignore willayd Cython cpython SSIZE VARARGS struct MODINIT Werror dylib tracepoints watchpoints libthread cfunctions kwargs methodobject tstate nargs Vectorcall Tstate nargsf kwnames oparg ceval throwflag DECREF MODINIT SIGABRT pthread pylifecycle Watchpoint Disp watchpoint curexc psize unicodeobject refcnt cfunction argstuple kwdict SIGSEGV libc Traceback libpython
---

[Python extensions](https://docs.python.org/3/extending/index.html) are a key component in making Python libraries fast. With an extension, you have the ability to write code in a lower-level language like C or C++ but still interact with that code via the Python runtime. Many high-performance scientific Python libraries use this type of architecture, whether through hand-writing a C/C++ extension(s) and/or generating them using a Python to C/C++ *transpiler* like [Cython](https://cython.org/).

This has tradeoffs for a library author. While Python is an interpreted language, extensions are typically written in languages that need to be compiled. Extensions also cannot be debugged with pdb. However, as you'll see in the following sections, pdb is heavily influenced by a lot of the tooling used for extension debugging, so if you worked through [the first article in this debugging series]({% post_url 2023-02-08-fundamental-python-debugging-part-1-python %}) you should have a solid foundation to build off of.

## Setting up our environment

A challenge we didn't face in the previous article was cross-platform tooling. pdb works regardless of your OS and architecture, but as we move further down into the stack we have to use tools more tailored to our environment.

Writing installation and usage instructions for all platforms would be quite the task. To abstract all of the nuances and make following through this guide easier, this guide assumes you will be using the docker image hosted at [willayd/cpython-debugging](https://hub.docker.com/r/willayd/cpython-debugging). This docker image contains the following items:

* [gcc](https://gcc.gnu.org/), which we use to build extensions
* [CPython](https://github.com/python/cpython) source code located in /clones/cpython
* A development build of Python pre-installed
* A custom build of ``gdb`` which knows about the development Python installation

Not all of these elements are required, but they all make debugging easier.

To get started with the image, be sure to first install the [docker engine](https://docs.docker.com/engine/install), at which point you can then:

```sh
docker pull willayd/cpython-debugging
```

A quick ``docker image`` should show that same image on your local machine. Once you have the image installed, you will want to choose a location on your host computer to mount into the container you will run based off of that image, so something like:

```sh
docker run --rm -it -w /data -v <PATH_TO_YOUR_WORK>:/data willayd/cpython-debugging
```

The ``-v`` flag here maps the part of its argument preceding the ``:`` and locates it on your host computer. It then mounts that location from your host computer to the path specified after the ``:`` within the container, which we've chosen above as ``/data``. Note that you can use shell expansion of environment variables like ``-v ${HOME}/code:/data`` if you have your work locally in a ``code`` subdirectory of your home directory. Even simpler, you could do ``-v ${PWD}:/data`` if your shell is already within the directory you want to mount.

## Building our first extension

Let's start with the following code in a file named ``debugging_demo.c``:

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *
say_hello_and_return_none (PyObject *self, PyObject *args)
{
  printf ("Hello from the extension\n");
  Py_RETURN_NONE;
}

static PyMethodDef debugging_demo_methods[] = {
  {"say_hello_and_return_none", say_hello_and_return_none, METH_VARARGS,
   "Says hello and returns none."},
  {NULL, NULL, 0, NULL}  /* Sentinel */
};

static struct PyModuleDef debugging_demo_module = {
  PyModuleDef_HEAD_INIT,
  .m_name = "debugging_demo",
  .m_doc = "A simple extension to showcase debugging",
  .m_size = 0,
  .m_methods = debugging_demo_methods
};

PyMODINIT_FUNC PyInit_debugging_demo(void)
{
  return PyModuleDef_Init(&debugging_demo_module);
}
```

I've saved this locally under ``~/code-demos``, so I'm going to launch my docker container with ``docker run --rm -it -w /data -v ${HOME}/code-demos:/data willayd/cpython-debugging``. A quick ``ls`` should confirm you have mounted everything properly:

```sh
willayd@willayd:~$ docker run --rm -it -w /data -v ${HOME}/code-demos:/data willayd/cpython-debugging
root@4a6161a82673:/data# ls
debugging_demo.c
root@4a6161a82673:/data#
```

We can build our C module into a shared library, after which we will be able to load it into Python.

```sh
root@12a481d4fa4c:/data# gcc -g3 -Wall -Werror -std=c17 -shared -fPIC -I/usr/local/include/python3.10d debugging_demo.c -o debugging_demo.so
root@12a481d4fa4c:/data# ls
debugging_demo.c  debugging_demo.so
```

``gcc`` is our tool for building the code, and all of the flags we provide here are documented in the [gcc Command Options](https://gcc.gnu.org/onlinedocs/gcc/Invoking-GCC.html).

``-g3`` instructs gcc to insert debugging information into the target, including macros. Without this, you may not properly be able to debug your application, may be unable to inspect source code, and may see things like ``optimized out`` when inspecting variables in gcc.

``-Wall`` turns on a lot of warnings (not all) and pairs well with ``-Werror``. For new C developers, I always suggest using these two. Coming from higher level languages like Python you may be used to ignoring warnings, but in C most warnings you get as a new developer really are critical coding errors.

``-shared`` and ``-fPIC`` are both required for building a shared library, and ``-I/usr/local/include/python3.10d`` allows gcc to find our ``Python.h`` header file. All of these are necessary to make our extension loadable from Python.

``-o debugging_demo.so`` created our shared library with an ``.so`` extension, which is common on GNU/Linux platforms. On macOS you may see a similar concept with a ``.dylib`` extension, whereas Windows has ``.dll``.

Now that this shared library is available, it can be loaded, inspected and executed from the Python interpreter.

```sh
root@12a481d4fa4c:/data# python3
Python 3.10.10+ (heads/3.10:bac3fe7, Feb 22 2023, 05:56:35) [GCC 11.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import debugging_demo
>>> debugging_demo.__doc__
'A simple extension to showcase debugging'
>>> dir(debugging_demo)
['__doc__', '__file__', '__loader__', '__name__', '__package__', '__spec__', 'say_hello_and_return_none']
>>> debugging_demo.say_hello_and_return_none.__doc__
'Says hello and returns none.'
>>> debugging_demo.say_hello_and_return_none()
Hello from the extension
```

## Inspecting things with gdb

If we wanted to look at the intermediate state of things, we can pause execution and move around the stack like we did with ``pdb`` in the previous article, but this time we will be using ``gdb``. To get started, simply run ``gdb python3``. Thereafter, ``help`` is a good place to start.

```sh
(gdb) help
List of classes of commands:

aliases -- User-defined aliases of other commands.
breakpoints -- Making program stop at certain points.
data -- Examining data.
files -- Specifying and examining files.
internals -- Maintenance commands.
obscure -- Obscure features.
running -- Running the program.
stack -- Examining the stack.
status -- Status inquiries.
support -- Support facilities.
text-user-interface -- TUI is the GDB text based interface.
tracepoints -- Tracing of program execution without stopping the program.
user-defined -- User-defined commands.

Type "help" followed by a class name for a list of commands in that class.
Type "help all" for the list of all commands.
Type "help" followed by command name for full documentation.
Type "apropos word" to search for commands related to "word".
Type "apropos -v word" for full documentation of commands related to "word".
Command name abbreviations are allowed if unambiguous.
(gdb)
```

Compared to ``pdb``, there are way more features within ``gdb`` to sift through. ``apropos`` or going through ``help all`` may be a good place to start. The help menu by default uses a very simple pager; instead you may find it useful to open the help in something like ``less`` using a pipe, i.e. ``pipe help all | less``.

The ``help status`` subsection introduces us to the ``info`` command. ``info breakpoint`` always lists your breakpoints, of which we have none right now.

```sh
(gdb) info breakpoint
No breakpoints or watchpoints.
```

``help break`` gives great details on how to set a breakpoint. For now, let's go ahead and enter ``break say_hello_and_return_none`` to enter the debugger when our function starts to execute.

```sh
(gdb) break say_hello_and_return_none
Function "say_hello_and_return_none" not defined.
Make breakpoint pending on future shared library load? (y or [n]) y
Breakpoint 1 (say_hello_and_return_none) pending.
```

Python has not yet loaded our shared library, so gdb isn't sure yet that this function exists. It will become available when we start running our program, so you can enter ``y`` when prompted above.

At this point go ahead and ``run`` to start the Python interpreter that gdb attached to. You can then import the module and execute the function, at which point gdb will come back to the forefront:

```sh
(gdb) run
Starting program: /usr/local/bin/python3
warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
Python 3.10.10+ (heads/3.10:bac3fe7, Feb 22 2023, 05:56:35) [GCC 11.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import debugging_demo
>>> debugging_demo.say_hello_and_return_none()

Breakpoint 1, say_hello_and_return_none (self=0x7f4de7360230, args=0x7f4de7674250) at debugging_demo.c:7
7      printf ("Hello from the extension\n");
```

Similar to ``pdb`` we have a ``backtrace`` command (or ``bt`` shortcut) to inspect the call stack. Unlike pdb, this shows the call sequence tracing from the bottom up rather than the top down.

```sh
(gdb) run
#0  say_hello_and_return_none (self=0x7f4de7360230, args=0x7f4de7674250) at debugging_demo.c:7
#1  0x0000558c96fed0cb in cfunction_call (func=0x7f4de73603b0, args=<optimized out>, kwargs=<optimized out>)
    at Objects/methodobject.c:552
#2  0x0000558c96e0a1c3 in _PyObject_MakeTpCall (tstate=tstate@entry=0x558c97f030b0,
    callable=callable@entry=0x7f4de73603b0, args=args@entry=0x7f4de76ea7c0, nargs=<optimized out>,
    keywords=keywords@entry=0x0) at Objects/call.c:215
#3  0x0000558c96ec1baa in _PyObject_VectorcallTstate (tstate=0x558c97f030b0, callable=0x7f4de73603b0, args=0x7f4de76ea7c0,
    nargsf=<optimized out>, kwnames=0x0) at ./Include/cpython/abstract.h:112
#4  0x0000558c96ec6185 in PyObject_Vectorcall (kwnames=0x0, nargsf=9223372036854775808, args=0x7f4de76ea7c0,
    callable=0x7f4de73603b0) at ./Include/cpython/abstract.h:123
#5  call_function (tstate=tstate@entry=0x558c97f030b0, trace_info=trace_info@entry=0x7fffe84db900,
    pp_stack=pp_stack@entry=0x7fffe84db8d0, oparg=oparg@entry=0, kwnames=kwnames@entry=0x0) at Python/ceval.c:5893
#6  0x0000558c96ed355e in _PyEval_EvalFrameDefault (tstate=0x558c97f030b0, f=0x7f4de76ea650, throwflag=<optimized out>)
    at Python/ceval.c:4181
```

Each frame is numbered on the left hand side from 0 (most-recent frame). You can use ``up`` and ``down`` to navigate the call stack, or you can use the ``frame`` command / ``f`` shortcut to jump to any particular frame.

Let us go ahead and jump to frame number 2, which is in the cpython source code at ``Objects/call.c`` on line 215. We can then use the ``list`` / ``l`` commands that pdb also has to look at that code.

```sh
(gdb) f 2
#2  0x0000558c96e0a1c3 in _PyObject_MakeTpCall (tstate=tstate@entry=0x558c97f030b0,
    callable=callable@entry=0x7f4de73603b0, args=args@entry=0x7f4de76ea7c0, nargs=<optimized out>,
    keywords=keywords@entry=0x0) at Objects/call.c:215
215          result = call(callable, argstuple, kwdict);
(gdb) l
210      }
211
212      PyObject *result = NULL;
213      if (_Py_EnterRecursiveCall(tstate, " while calling a Python object") == 0)
214      {
215          result = call(callable, argstuple, kwdict);
216          _Py_LeaveRecursiveCall(tstate);
217      }
218
219      Py_DECREF(argstuple);
```

Let's do ``f 0`` to get back to the most current frame. There you can use ``next`` / ``n`` to advance to the next line, and then ``continue`` / ``c`` to let the program continue.

```sh
(gdb) f 0
#0  say_hello_and_return_none (self=0x7f4de7360230, args=0x7f4de7674250) at debugging_demo.c:7
7      printf ("Hello from the extension\n");
(gdb) n
Hello from the extension
8      Py_RETURN_NONE;
(gdb) c
Continuing.
>>>
```

At the very end we get back to our Python interpret. You can ``quit()`` out of this to get back to gdb, and then ``exit`` gdb to get back to the shell.

```sh
>>> quit()
[Inferior 1 (process 57) exited normally]
(gdb) exit
root@ba83cd50f6ec:/data#
```

## Debugging Segmentation Faults

Let's introduce an off-by-one programming error into our source code. We can create a new ``debugging_demo2.c`` file with similar but updated content:

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define NUM_WORDS 4

static PyObject *
say_hello_and_return_none (PyObject *self, PyObject *args)
{
  const char* words[NUM_WORDS] = {
    "Hello",
    "from",
    "the",
    "extension"
  };

  for (int i = 0; i <= NUM_WORDS; i++) {
    printf ("%s ", words[i]);
  }

  printf("\n");
  Py_RETURN_NONE;
}

static PyMethodDef debugging_demo2_methods[] = {
  {"say_hello_and_return_none", say_hello_and_return_none, METH_VARARGS,
   "Says hello and returns none."},
  {NULL, NULL, 0, NULL}  /* Sentinel */
};

static struct PyModuleDef debugging_demo2_module = {
  PyModuleDef_HEAD_INIT,
  .m_name = "debugging_demo2",
  .m_doc = "A simple extension to showcase debugging",
  .m_size = 0,
  .m_methods = debugging_demo2_methods
};

PyMODINIT_FUNC PyInit_debugging_demo2(void)
{
  return PyModuleDef_Init(&debugging_demo2_module);
}
```

Compile with ``gcc -g3 -Wall -Werror -std=c17 -shared -fPIC -I/usr/local/include/python3.10d debugging_demo2.c -o debugging_demo2.so``. A quick ``python3 -c "import debugging_demo2; debugging_demo2.say_hello_and_return_none()"`` this time will likely give you a segmentation fault, with no real error message.

```sh
root@ba83cd50f6ec:/data# python3 -c "import debugging_demo2; debugging_demo2.say_hello_and_return_none()"
Segmentation fault (core dumped)
```

Fortunately, gdb will automatically stop execution on a segfault and give you the ability to inspect your program. Let's start this program using the ``--args`` argument to gdb, which will allow us to forward arguments like ``-c "..."`` to the program gdb attaches to (here python3):

```sh
root@ba83cd50f6ec:/data# gdb --args python3 -c "import debugging_demo2; debugging_demo2.say_hello_and_return_none()"
GNU gdb (GDB) 12.1
Copyright (C) 2022 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
...
For help, type "help".
Type "apropos word" to search for commands related to "word"...
Reading symbols from python3...
(gdb)
```

Enter ``run`` and things will pause when the segmentation fault occurs:

```sh
(gdb) run
Starting program: /usr/local/bin/python3 -c import\ debugging_demo2\;\ debugging_demo2.say_hello_and_return_none\(\)
warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".

Program received signal SIGSEGV, Segmentation fault.
0x00007ffb409dc97d in ?? () from /lib/x86_64-linux-gnu/libc.so.6
(gdb)
```

f we inspect the backtrace, we will see that the first three frames are from ``/lib/x86_64-linux-gnu/libc.so``, which is the part of the standard library on GNU/Linux.

```sh
(gdb) bt
#0  0x00007ffb409dc97d in ?? () from /lib/x86_64-linux-gnu/libc.so.6
#1  0x00007ffb408b5db1 in ?? () from /lib/x86_64-linux-gnu/libc.so.6
#2  0x00007ffb4089f81f in printf () from /lib/x86_64-linux-gnu/libc.so.6
#3  0x00007ffb405b5245 in say_hello_and_return_none (self=0x7ffb4065dc10, args=0x7ffb406e4250) at debugging_demo.c:15
#4  0x000055bed6af30cb in cfunction_call (func=0x7ffb406a2b10, args=<optimized out>, kwargs=<optimized out>)
    at Objects/methodobject.c:552
```

In contrast to the last 2 frames, there is also barely any function information. This is because these libraries are heavily optimized without any debugging symbols (remember the ``-g3`` flag we using during compilation) so gdb can't do much besides tell us the memory location of the calls. If you ever try to debug a program and can't see the symbols you are looking for, keep this in mind.

In any case, we are going to assume there is no bug in the standard library and jump back to f 3 to inspect our code. There a quick ``info locals`` will tell us about the local variables.

```sh
(gdb) f 3
#3  0x00007ffb405b5245 in say_hello_and_return_none (self=0x7ffb4065dc10, args=0x7ffb406e4250) at debugging_demo.c:15
15       printf ("%s ", words[i]);
(gdb) info locals
i = 4
words = {0x7ffb405b6000 "Hello", 0x7ffb405b6006 "from", 0x7ffb405b600b "the", 0x7ffb405b600f "extension"}
```

Since C is a 0-indexed language, the expression ``words[i]`` tries to access memory that is out of bounds, which is the root cause of our segmentation fault:

```sh
(gdb) p words[3]
$1 = 0x7ffb405b600f "extension"
(gdb) p words[i]
$2 = 0x2e <error: Cannot access memory at address 0x2e>
```

A quick ``l`` lists the code surrounding this function.

```sh
(gdb) l
12       "the",
13       "extension"
14     };
15
16     for (int i = 0; i <= NUM_WORDS; i++) {
17       printf ("%s ", words[i]);
18     }
19
20     printf("\n");
21     Py_RETURN_NONE;
```

The error is on line 14 and to have this program execute properly we would need to change ``for (int i = 0; i <= NUM_WORDS; i++)`` to ``for (int i = 0; i < NUM_WORDS; i++)``, keeping our array access in bounds.

As an aside, if we had turned on optimization when compiling this via the ``-O2`` flag, gcc would have warned and then errored (as long as you use ``-Werror``) up front. But that would have made debugging less fun.

```sh
root@ba83cd50f6ec:/data# gcc -g3 -O2 -Wall -Werror -std=c17 -shared -fPIC -I/usr/local/include/python3.10d debugging_demo2.c -o debugging_demo2.so
debugging_demo2.c: In function 'say_hello_and_return_none':
debugging_demo2.c:17:5: error: iteration 4 invokes undefined behavior [-Werror=aggressive-loop-optimizations]
   17 |     printf ("%s ", words[i]);
      |     ^~~~~~~~~~~~~~~~~~~~~~~~
debugging_demo2.c:16:21: note: within this loop
   16 |   for (int i = 0; i <= NUM_WORDS; i++) {
      |                     ^
cc1: all warnings being treated as errors
```

## Debugging Python->C data exchange

CPython distributes a [gdb python extension](https://sourceware.org/gdb/onlinedocs/gdb/Python.html#Python) that bridges the gap between what you as a Python developer see at runtime versus what gdb knows about the objects it sees at a lower level. This extension is housed in the [CPython source code](https://github.com/python/cpython/blob/main/Tools/gdb/libpython.py), which we also have hanging around at ``/clones`` in our Docker image.

Let's continue expanding on our previous extension, this time naming it ``debugging_demo3.c``. Rather than being self contained, the new extension will print whatever name you pass to it through the Python interpreter. Our initial structure looks like this:

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define NUM_WORDS 4

static PyObject *
say_hello_and_return_none (PyObject *self, PyObject *args)
{
  PyObject *name;
  if (!PyArg_ParseTuple(args, "O", &name)) {
    return NULL;
  }

  const char *str = PyUnicode_AsUTF8(name);
  printf("Hello, %s\n", str);
  Py_RETURN_NONE;
}

static PyMethodDef debugging_demo3_methods[] = {
  {"say_hello_and_return_none", say_hello_and_return_none, METH_VARARGS,
   "Says hello and returns none."},
  {NULL, NULL, 0, NULL}  /* Sentinel */
};

static struct PyModuleDef debugging_demo3_module = {
  PyModuleDef_HEAD_INIT,
  .m_name = "debugging_demo3",
  .m_doc = "A simple extension to showcase debugging",
  .m_size = 0,
  .m_methods = debugging_demo3_methods
};

PyMODINIT_FUNC PyInit_debugging_demo3(void)
{
  return PyModuleDef_Init(&debugging_demo3_module);
}
```

We need to build this extension just as we have done before, this time using ``gcc -g3 -Wall -Werror -std=c17 -shared -fPIC -I/usr/local/include/python3.10d debugging_demo3.c -o debugging_demo3.so``.

If you look closely at the source code above we have introduced [PyArg_ParseTuple](https://docs.python.org/3/c-api/arg.html), which handles unpacking function arguments into local variables. Our function takes 1 and only 1 argument in its current form; attempting to call it with anything else will set the global Python error indicator, hit the ``return NULL;`` statement, and propagate the error back to the Python runtime. That's a lot of power packed into a few lines of code.

```sh
root@ba83cd50f6ec:/data# python3
Python 3.10.10+ (heads/3.10:bac3fe7, Feb 22 2023, 05:56:35) [GCC 11.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import debugging_demo3
>>> debugging_demo3.say_hello_and_return_none("Will")
Hello, Will
>>> debugging_demo3.say_hello_and_return_none()
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: function takes exactly 1 argument (0 given)
>>> debugging_demo3.say_hello_and_return_none("Will", "Ayd")
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
TypeError: function takes exactly 1 argument (2 given)
```

Things work great until you try passing through something that is not a unicode object.

```sh
>>> debugging_demo3.say_hello_and_return_none(555)
Hello, (null)
Fatal Python error: _Py_CheckFunctionResult: a function returned a result with an exception set
Python runtime state: initialized
TypeError: bad argument type for built-in operation

The above exception was the direct cause of the following exception:

SystemError: <built-in function say_hello_and_return_none> returned a result with an exception set

Current thread 0x00007f5dd4cbb740 (most recent call first):
  File "<stdin>", line 1 in <module>

Extension modules: debugging_demo3 (total: 1)
Aborted (core dumped)
```

This time the program aborted instead of having a segmentation fault. That said, gdb will still allow you to jump in and inspect the state of things prior to termination.

```sh
root@ba83cd50f6ec:/data# gdb --args python3 -c "import debugging_demo3; debugging_demo3.say_hello_and_return_none(555)"
Reading symbols from python3...
(gdb) run
Starting program: /usr/local/bin/python3 -c import\ debugging_demo3\;\ debugging_demo3.say_hello_and_return_none\(555\)
warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
Hello, (null)
Fatal Python error: _Py_CheckFunctionResult: a function returned a result with an exception set
Python runtime state: initialized
TypeError: bad argument type for built-in operation

The above exception was the direct cause of the following exception:

SystemError: <built-in function say_hello_and_return_none> returned a result with an exception set

Current thread 0x00007f9b27e91740 (most recent call first):
  File "<string>", line 1 in <module>

Extension modules: debugging_demo3 (total: 1)

Program received signal SIGABRT, Aborted.
0x00007f9b27f2aa7c in pthread_kill () from /lib/x86_64-linux-gnu/libc.so.6
```

When you look at the backtrace here, you won't see any of our user code:

```sh
(gdb) bt
#0  0x00007f9b27f2aa7c in pthread_kill () from /lib/x86_64-linux-gnu/libc.so.6
#1  0x00007f9b27ed6476 in raise () from /lib/x86_64-linux-gnu/libc.so.6
#2  0x00007f9b27ebc7f3 in abort () from /lib/x86_64-linux-gnu/libc.so.6
#3  0x0000555c45a8505b in fatal_error_exit (status=<optimized out>) at Python/pylifecycle.c:2553
#4  0x0000555c45a895c7 in fatal_error (fd=2, header=header@entry=1,
    prefix=prefix@entry=0x555c45c08a60 <__func__.18> "_Py_CheckFunctionResult",
    msg=msg@entry=0x555c45c08528 "a function returned a result with an exception set", status=status@entry=-1)
    at Python/pylifecycle.c:2734
#5  0x0000555c45a89630 in _Py_FatalErrorFunc (func=func@entry=0x555c45c08a60 <__func__.18> "_Py_CheckFunctionResult",
```

This is a bit unfortunate because we can't directly trace back to our function. With that said, the message ``a function returned a result with an exception set`` clues us in on where we need to look. CPython manages one global error indicator queryable via [PyErr_Occurred()](https://docs.python.org/3/c-api/exceptions.html).

To do this, let's set a ``break say_hello_and_return_none`` to pause execution when we enter our function. Then ``run`` to get to that point and add a ``watch PyErr_Occurred()`` to the mix.

```sh
(gdb) break say_hello_and_return_none
Breakpoint 1 at 0x7f0a8fbf5200: file debugging_demo3.c, line 8.
(gdb) run
The program being debugged has been started already.
Start it from the beginning? (y or n) y
Starting program: /usr/local/bin/python3 -c import\ debugging_demo3\;\ debugging_demo3.say_hello_and_return_none\(555\)
warning: Error disabling address space randomization: Operation not permitted
[Thread debugging using libthread_db enabled]
Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".

Breakpoint 1, say_hello_and_return_none (self=0x7f58e60305f0, args=0x7f58e5fe98b0) at debugging_demo3.c:8
8    {
(gdb) watch PyErr_Occurred()
Watchpoint 2: PyErr_Occurred()
```

At this point ``info break`` should show us the two conditions under which gdb will pause, either on ``say_hello_and_return_none`` entry or when the ``PyErr_Occurred()`` value changes.

```sh
(gdb) info break
Num     Type           Disp Enb Address            What
1       breakpoint     keep y   0x00007f58e5f87200 in say_hello_and_return_none at debugging_demo3.c:8
     breakpoint already hit 1 time
2       watchpoint     keep y                      PyErr_Occurred()
```

Type ``c`` to continue along and you will see that the watchpoint gets hit:

```sh
(gdb) c
Continuing.

Watchpoint 2: PyErr_Occurred()

Old value = (PyObject *) 0x0
New value = (PyObject *) 0x55ccfb73cc20 <_PyExc_TypeError>
_PyErr_Restore (tstate=tstate@entry=0x55ccfcb82930, type=type@entry=0x55ccfb73cc20 <_PyExc_TypeError>, value=value@entry=0x7f58e6057640, traceback=0x0) at Python/errors.c:60
60       tstate->curexc_value = value;
```

The watchpoint wasn't hit within our code, but internal to CPython. No matter - we can inspect the backtrace and see what point in our code base this might happen at.

```sh
(gdb) bt
#0  _PyErr_Restore (tstate=tstate@entry=0x55ccfcb82930, type=type@entry=0x55ccfb73cc20 <_PyExc_TypeError>,
    value=value@entry=0x7f58e6057640, traceback=0x0) at Python/errors.c:60
#1  0x000055ccfb455d60 in _PyErr_SetObject (tstate=tstate@entry=0x55ccfcb82930,
    exception=exception@entry=0x55ccfb73cc20 <_PyExc_TypeError>, value=value@entry=0x7f58e6057640) at Python/errors.c:189
#2  0x000055ccfb455f59 in _PyErr_SetString (tstate=0x55ccfcb82930, exception=0x55ccfb73cc20 <_PyExc_TypeError>,
    string=string@entry=0x55ccfb645698 "bad argument type for built-in operation") at Python/errors.c:235
#3  0x000055ccfb455fdd in PyErr_BadArgument () at Python/errors.c:667
#4  0x000055ccfb402060 in PyUnicode_AsUTF8AndSize (unicode=<optimized out>, psize=psize@entry=0x0)
    at Objects/unicodeobject.c:4245
#5  0x000055ccfb402195 in PyUnicode_AsUTF8 (unicode=<optimized out>) at Objects/unicodeobject.c:4265
#6  0x00007f58e5f87245 in say_hello_and_return_none (self=0x7f58e60305f0, args=0x7f58e5fe98b0) at debugging_demo3.c:14
```

Frame 6 is ``say_hello_and_return_none``, specifically on line 14. You can jump back to that and see the line being called.

```sh
(gdb) f 6
#6  0x00007f58e5f87245 in say_hello_and_return_none (self=0x7f58e60305f0, args=0x7f58e5fe98b0) at debugging_demo3.c:14
14     const char *str = PyUnicode_AsUTF8(name);
```

We know from our function invocation that we are passed the value ``555`` as an argument to the function call. However, you wouldn't know this by trying to print the object in gdb.

```sh
(gdb) p name
$1 = (PyObject *) 0x7f58e6013bc0
(gdb) p *name
$2 = {ob_refcnt = 4, ob_type = 0x55ccfb73f180 <PyLong_Type>}
```

We get *some* information when dereferencing this object about the basic ``PyObject`` struct members. But we'd have to muck around a bit more to see the members that are relevant to longs, or whatever object type it is we inspect.

This is where the gdb extension becomes a really powerful abstraction tool. First, we need to load the extension into gdb. This can be done at runtime with the ``source`` command pointing to the extension file. In our docker image, this would mean

```sh
(gdb) source /clones/cpython/Tools/gdb/libpython.py
```

Once you have loaded the extension, the default printing mechanism becomes a lot more familiar to Python users.

```sh
(gdb) p name
$3 = 555
```

This confirms that the object we have on this line is the same we provided to the function call, so nothing way out of the ordinary is going on. Since the global ``PyErr_Occurred()`` indicator was set, we can use ``PyErr_Print()`` to get information from the Python runtime about what went wrong. Note that calling this clears the error indicator.

```sh
(gdb) call PyErr_PrintEx(0)
TypeError
(gdb) p PyErr_Occurred()
$4 = 0x0
```

We called ``PyUnicode_AsUTF8`` with a ``PyLong`` object even though it expected ``PyUnicode``. In the Python runtime this would automatically trigger an exception and stop things immediately. C doesn't have built-in error handling, so things continue unless you explicitly handle the issue.

Following the pattern of [CPython Exception Handling](https://docs.python.org/3/c-api/exceptions.htmlpyerr), we are going to slightly modify our source code to look like this:

```c
#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define NUM_WORDS 4

static PyObject *
say_hello_and_return_none (PyObject *self, PyObject *args)
{
  PyObject *name;
  if (!PyArg_ParseTuple(args, "O", &name)) {
    return NULL;
  }

  const char *str = PyUnicode_AsUTF8(name);
  if (str == NULL) {
    return NULL;
  }

  printf("Hello, %s\n", str);
  Py_RETURN_NONE;
}

static PyMethodDef debugging_demo3_methods[] = {
  {"say_hello_and_return_none", say_hello_and_return_none, METH_VARARGS,
   "Says hello and returns none."},
  {NULL, NULL, 0, NULL}  /* Sentinel */
};

static struct PyModuleDef debugging_demo3_module = {
  PyModuleDef_HEAD_INIT,
  .m_name = "debugging_demo3",
  .m_doc = "A simple extension to showcase debugging",
  .m_size = 0,
  .m_methods = debugging_demo3_methods
};

PyMODINIT_FUNC PyInit_debugging_demo3(void)
{
  return PyModuleDef_Init(&debugging_demo3_module);
}
```

The ``if (str == NULL)`` is our way of handling a failed ``PyUnicode_AsUTF8`` call. By propagating that ``NULL`` value up the call stack, CPython will gracefully handle the error for us when we get back to the Python runtime. To confirm, recompile and trying passing the same argument to the function.

```sh
(gdb) exit
A debugging session is active.

     Inferior 1 [process 515] will be killed.

Quit anyway? (y or n) y
root@ba83cd50f6ec:/data# gcc -g3 -Wall -Werror -std=c17 -shared -fPIC -I/usr/local/include/python3.10d debugging_demo3.c -o debugging_demo3.so
root@ba83cd50f6ec:/data# python3 -c "import debugging_demo3; debugging_demo3.say_hello_and_return_none(555)"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
TypeError: bad argument type for built-in operation
```

We still have an error, but the error is the built-in ``TypeError`` that we can handle in our Python code if we wanted, instead of the ``SIGABRT`` that shut down the application previously.

While not in scope for this article, there are many ways you can improve the above function. You could either change the [format string](https://docs.python.org/3/c-api/arg.html#strings-and-buffers) provided to ``PyArg_ParseTuple`` to map to something else besides a ``PyObject ``*, or alternately mix in a call to ``PyObject_Str`` to coerce any object to a unicode object prior to the ``PyUnicode_AsUTF8`` call.

## Closing Thoughts

Understanding how C and Python interacted was something I struggled with for years. Once unlocked, I found knowledge of how to interact at the lower levels using gdb to be invaluable. I can only hope that this article lays a good foundation for you to build upon.

The only other advice I can offer is to be patient! I've been at this for years and still find myself learning something new every day. Therein lies the true art of programming.

My next article will focus on using the [Cython debugger](https://cython.readthedocs.io/en/latest/src/userguide/debugging.html), which is implemented as a gdb extension. The knowledge in this article is a hugely important stepping stone towards that. If you can understand how to control and debug all of these components, you are in a very good spot when it comes to Python development.
