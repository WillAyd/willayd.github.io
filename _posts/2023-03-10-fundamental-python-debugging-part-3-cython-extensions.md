---
title: "Fundamental Python Debugging Part 3 - Cython Extensions"
date: 2023-03-10T00:00:00
categories:
  - debugging
tags:
  - python
  - cython
# cSpell:ignore willayd Cython cpython Werror cygdb transpiles mdef NOARGS CYTHON cpdef cdef proto Disp CYTHON
---

For the unaware, Cython is a transpiler from a Python-like syntax into C files. This gets you close to C performance while writing files that aren't *that* dissimilar from Python. It is used extensively in the scientific Python community to generate high-performance extensions. A common approach to optimize Python libraries is to make sure you are as efficient as possible in pure Python, before building your code in Cython, and commonly as a last resort writing your C/C++ extensions by hand.

In spite of this pattern we are introducing Cython as the third part of the debugging series, after already having debugged C extensions. Why is that? Well, it turns out that the Cython debugger is in fact a [gdb python extension](https://sourceware.org/gdb/onlinedocs/gdb/Python.html#Python), which we saw CPython also leverage in the last chapter. We aren't doing anything novel in this chapter but just walking through some of the conveniences the ``cygdb` extension provides (interested users can find the source code [here](https://github.com/cython/cython/blob/master/Cython/Debugger/Cygdb.py)).

If you haven't read the [previous article on debugging Python extensions with gdb]({% post_url 2023-02-22-fundamental-python-debugging-part-2-python %}), I highly recommend that you do so before continuing here. Although writing Cython can be thought of as a stepping stone to writing C/C++ extensions, the inverse is true when it comes to debugging.

## Setting up our environment

For this chapter we will leverage the same image as in the last, so start with:

```sh
docker pull willayd/cpython-debugging
```

In addition to the items outlined in the previous chapter, this image also includes Cython as a pip-installed package. If you don't care to use the docker image you can also follow the instructions in the [Debugging your Cython program documentation](https://cython.readthedocs.io/en/latest/src/userguide/debugging.html), but be aware that some of the interactions between Cython, gdb and Python aren't very intuitive, especially if using Python installed as a virtual image.

If using the docker image above, be sure to run it as a container and mount a local directory for development into the container at ``/host``. As in the previous section, I will be putting my work in a directory called ``~/code-demos``.

```sh
willayd@willayd:~$ docker run --rm -it -w /data -v ${HOME}/code-demos:/data willayd/cpython-debugging
```

## Build our first Cython extension

We are going to start with the same extension we created in the previous chapter. Let's create a file named ``debugging_cython.pyx`` in the folder on your computer that you mounted into docker and insert these contents:

```python
def say_hello_and_return_none():
    print("Hello from the Cython extension")
```

That's it! From here we now have two steps we need to follow to get this converted into an importable extension:

1. Transpile the Cython file into a C module
2. Build a shared library from the C module

The ``cython`` command can help us with Step 1; Step 2 builds on a lot of knowledge from the previous chapter. Here are the commands:

```sh
root@f241800d6a12:/data# cython --gdb debugging_cython.pyx
root@f241800d6a12:/data# gcc -g3 -Wall -Werror -std=c17 -shared -fPIC -I/usr/local/include/python3.10d debugging_cython.c -o debugging_cython.so
```

With the extension built, you can import the module and call the function.

```sh
root@f241800d6a12:/data# python3
>>> import debugging_cython
>>> debugging_cython.say_hello_and_return_none()
Hello from the Cython extension
```

## Using cygdb

If you inspect the output of ``debugging_cython.c`` which was generated in the previous section, you could debug it using ``gdb`` as if it were a normal C module, because it is. It certainly doesn't look that anything that you would have written by hand, but there isn't any real magic to what is happening here; Cython takes Python-like code and transpiles a C file out of it. The rest of the tooling that we've seen in the previous chapter can pick things up from there. However, because the file was auto-generated you lose a lot of the abstractions that you get from writing Python-like code, and end up stepping through a tangled web of variables you aren't familiar with in gdb. ``pdb`` cannot debug Cython files for us, so we need to use ``cygdb``. We can then set a breakpoint at our function using the ``cy break`` command and open up a Python interpreter with ``cy run``.

```sh
root@fad66408f996:/data# cygdb
(gdb) cy break say_hello_and_return_none
Function "__pyx_pw_16debugging_cython_1say_hello_and_return_none" not defined.
Breakpoint 1 (__pyx_pw_16debugging_cython_1say_hello_and_return_none) pending.
(gdb) cy run
Python 3.10.10+ (heads/3.10:bac3fe7, Feb 22 2023, 05:56:35) [GCC 11.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

With the Python interpreter running let us import and execute our function.

```sh
>>> import debugging_cython
>>> debugging_cython.say_hello_and_return_none()

Breakpoint 1, __pyx_pw_16debugging_cython_1say_hello_and_return_none (__pyx_self=0x0, unused=0x0) at debugging_cython.c:1202
1202   PyObject *__pyx_r = 0;
1    def say_hello_and_return_none():
```

We've hit a breakpoint at line 1202 of the generated ``debugging_cython.c`` file. The commands the Cython debugger exposes are not really that different from what we saw with ``gdb`` in the previous chapter. The difference is that the ``gdb`` built-in commands will work as if you are debugging ``debugging_cython.c``, whereas the ``cygdb`` commands will work as if you are debugging ``debugging_cython.pyx``. Inputting ``list`` and then ``cy list`` will help us see this in action:

```sh
(gdb) list
         1    def say_hello_and_return_none():1197
1198 /* Python wrapper */
1199 static PyObject *__pyx_pw_16debugging_cython_1say_hello_and_return_none(PyObject *__pyx_self, CYTHON_UNUSED PyObject *unused); /*proto*/
1200 static PyMethodDef __pyx_mdef_16debugging_cython_1say_hello_and_return_none = {"say_hello_and_return_none", (PyCFunction)__pyx_pw_16debugging_cython_1say_hello_and_return_none, METH_NOARGS, 0};
1201 static PyObject *__pyx_pw_16debugging_cython_1say_hello_and_return_none(PyObject *__pyx_self, CYTHON_UNUSED PyObject *unused) {
1202   PyObject *__pyx_r = 0;
1203   __Pyx_RefNannyDeclarations
1204   __Pyx_RefNannySetupContext("say_hello_and_return_none (wrapper)", 0);
1205   __pyx_r = __pyx_pf_16debugging_cython_say_hello_and_return_none(__pyx_self);
1206
(gdb) cy list
>    1    def say_hello_and_return_none():
     2        print("Hello from the Cython extension")
```

``help cy`` gives a nice overview within ``gdb`` of the available commands. It is a much smaller set of commands than what ``gdb`` offers, but should cover the majority of needs in normal development.

```sh
(gdb) help cy

    Invoke a Cython command. Available commands are:

        cy import
        cy break
        cy step
        cy next
        cy run
        cy cont
        cy finish
        cy up
        cy down
        cy select
        cy bt / cy backtrace
        cy list
        cy print
        cy set
        cy locals
        cy globals
        cy exec

...
Type "help cy" followed by cy subcommand name for full documentation.
Type "apropos word" to search for commands related to "word".
Type "apropos -v word" for full documentation of commands related to "word".
Command name abbreviations are allowed if unambiguous.
```

## cpdef functions

Our previous program leveraged a ``def`` function, which Cython makes callable from the Python interpreter. Cython also offers ``cdef`` functions (not callable from Python) and ``cpdef`` functions, which essentially generate a ``def`` and a ``cdef`` for you. A detailed explanation of why you would choose those is outside the scope of this article; if you need a primer be sure to check out the wonderful [Cython language basics documentation](https://cython.readthedocs.io/en/latest/src/userguide/language_basics.html).

For debugging purposes, let's create ``debugging_cython2.pyx`` and change our function from ``def`` to ``cpdef``.

```python
cpdef say_hello_from_cpdef():
    print("Hello from the cpdef function")
```

If you are still running ``cygdb`` from the previous section, go ahead and ``exit`` to get back to your standard terminal. From there, we want to transpile and create our new shared library:

```sh
root@f241800d6a12:/data# cython --gdb debugging_cython2.pyx
root@f241800d6a12:/data# gcc -g3 -Wall -Werror -std=c17 -shared -fPIC -I/usr/local/include/python3.10d debugging_cython2.c -o debugging_cython2.so
```

Fire up ``cygdb`` again and set another breakpoint on that function:

```sh
(gdb) cy break say_hello_from_cpdef
Function "__pyx_f_17debugging_cython2_say_hello_from_cpdef" not defined.
Breakpoint 1 (__pyx_f_17debugging_cython2_say_hello_from_cpdef) pending.
Function "__pyx_pw_17debugging_cython2_1say_hello_from_cpdef" not defined.
Breakpoint 2 (__pyx_pw_17debugging_cython2_1say_hello_from_cpdef) pending.
```

What is interesting here is that we now have 2 breakpoints! The reason for this again is that ``cpdef`` generates two functions for us - one purely accessible from C and one accessible from Python. Go ahead and ``cy run`` to get the Python interpreter started; we will then run ``cy cont`` to continue past each breakpoint.

```sh
(gdb) cy run
Python 3.10.10+ (heads/3.10:bac3fe7, Feb 22 2023, 05:56:35) [GCC 11.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import debugging_cython2
>>> debugging_cython2.say_hello_from_cpdef()

Breakpoint 2, __pyx_pw_17debugging_cython2_1say_hello_from_cpdef (__pyx_self=<module at remote 0x7f1da030d6d0>, unused=0x0) at debugging_cython2.c:1227
1227   PyObject *__pyx_r = 0;
(gdb) cy list
  1222    }
  1223
  1224    /* Python wrapper */
  1225    static PyObject *__pyx_pw_17debugging_cython2_1say_hello_from_cpdef(PyObject *__pyx_self, CYTHON_UNUSED PyObject *unused); /*proto*/
  1226    static PyObject *__pyx_pw_17debugging_cython2_1say_hello_from_cpdef(PyObject *__pyx_self, CYTHON_UNUSED PyObject *unused) {
> 1227      PyObject *__pyx_r = 0;
  1228      __Pyx_RefNannyDeclarations
  1229      __Pyx_RefNannySetupContext("say_hello_from_cpdef (wrapper)", 0);
  1230      __pyx_r = __pyx_pf_17debugging_cython2_say_hello_from_cpdef(__pyx_self);
  1231
(gdb) cy cont

Breakpoint 1, __pyx_f_17debugging_cython2_say_hello_from_cpdef (__pyx_skip_dispatch=0) at debugging_cython2.c:1194
1194   PyObject *__pyx_r = NULL;
1    cpdef say_hello_from_cpdef():
(gdb) cy list
>    1    cpdef say_hello_from_cpdef():
     2        print("Hello from the cpdef function")
(gdb) cy cont
Hello from the cpdef function
>>> quit()
[Inferior 1 (process 105) exited normally]
```

Note that the ``cy list`` in the first breakpoint lists C source code, whereas the second ``cy list`` shows the Cython source code. Given the purpose of ``cpdef`` this may not be too surprising, but it may be confusing to new users.

## Managing cy break breakpoints

While ``cy break`` lets you create breakpoints, it does not give you any tools to delete, enable, disable, etc... However, you can work around this issue by using ``gdb's`` native commands for managing breakpoints, which we detailed on in the previous debugging article. Continuing with our example above, an ``info break`` yields the following:

```sh
(gdb) info break
Num     Type           Disp Enb Address            What
1       breakpoint     keep y   0x00007f1da010581d in __pyx_f_17debugging_cython2_say_hello_from_cpdef at debugging_cython2.c:1194
     breakpoint already hit 2 times
2       breakpoint     keep y   0x00007f1da01058c6 in __pyx_pw_17debugging_cython2_1say_hello_from_cpdef at debugging_cython2.c:1227
     breakpoint already hit 3 times
```

If you didn't want the first breakpoint to be hit from Cython, you ``delete 1`` or ``disable 1``.

```sh
(gdb) disable 1
(gdb) cy run
Python 3.10.10+ (heads/3.10:bac3fe7, Feb 22 2023, 05:56:35) [GCC 11.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import debugging_cython2
>>> debugging_cython2.say_hello_from_cpdef()

Breakpoint 2, __pyx_pw_17debugging_cython2_1say_hello_from_cpdef (__pyx_self=<module at remote 0x7f8825188650>, unused=0x0) at debugging_cython2.c:1227
1227   PyObject *__pyx_r = 0;
1227      PyObject *__pyx_r = 0;
(gdb) cy cont
Hello from the cpdef function
>>> debugging_cython2.say_hello_from_cpdef()

Breakpoint 2, __pyx_pw_17debugging_cython2_1say_hello_from_cpdef (__pyx_self=<module at remote 0x7f8825188650>, unused=0x0) at debugging_cython2.c:1227
1227   PyObject *__pyx_r = 0;
1227      PyObject *__pyx_r = 0;
(gdb) cy cont
Hello from the cpdef function
>>> quit()
[Inferior 1 (process 105) exited normally]
```

## Closing Thoughts

If you've made it this far - congratulations! Debugging as we've done in this three part series is not going to be the flashiest thing you do as a developer. However, I can guarantee that working with these tools at such a level will give you a critical foundation with which you can build upon. Whether you are a Python developer looking to go *lower level* for performance reasons, or you are a C/C++ developer looking to go *higher level* to work with good abstractions, having these debuggers at your disposal will let you move up and down your computing stack with relative ease. Now go forth and have fun!
