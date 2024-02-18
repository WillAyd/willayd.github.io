---
title: "Fundamental Python Debugging Part 1 - Python"
date: 2023-02-08T00:00:00
description: This blog post teaches you how to navigate pdb, the Python debugger. It is part 1 of a 3 part series.
categories:
  - debugging
tags:
  - python
# cSpell:ignore willayd Cython pythonic Traceback undisplay longlist tbreak retval unalias inue mainpyfile runscript Disp removeprefix isinstance whatis
---

The topic of debugging Python is well-covered. Regardless of whether you want to use your IDE interactively or work from a console with [pdb](https://docs.python.org/3/library/pdb.html), chances are this is not the first article you have read on the topic.

In spite of the wealth of content, I've found that most articles on debugging Python are singularly focused on debugging Python. That may not seem like such a bad thing at face value, but developing Python at an advanced level requires not only knowledge of the language itself, but also of lower level languages like C/C++. Being an expert in all of these languages at one time is near impossible, so knowing how to debug them effectively is critical.

Luckily, when viewed through the proper lens, there is a lot of overlap in the debugging tooling for these languages. The built-in Python pdb debugger borrows much of its utility from [gdb](https://sourceware.org/gdb/),  which will help you debug C/C++/Rust/Fortran, etc... gdb itself is extendable [using Python](https://sourceware.org/gdb/onlinedocs/gdb/Python.html#Python), and this extensibility is the reason why things like the [Cython debugger](https://cython.readthedocs.io/en/latest/src/userguide/debugging.html) exist.

Few if any other articles on debugging Python applications touch on these synchronicities. This and my next few blog posts attempt to highlight this for you and help you seamlessly transition across the aforementioned tools.

## Setting up your example

Let's start with a buggy script. This code isn't pythonic and you may be able to troubleshoot without even using a debugger, but that isn't important for this exercise. Go ahead and save the below snippet as ``buggy_program.py``:

```python
def buggy_loop():
    animals = ["dog", "cat", "turtle"]
    index = 0

    while index <= len(animals):
        print(f"The animal at index {index} is {animals[index]}")
        index += 1

if __name__ == "__main__":
    buggy_loop()
```

Executing this program with ``python buggy_program.py`` should yield:

```sh
The animal at index 0 is dog
The animal at index 1 is cat
The animal at index 2 is turtle
Traceback (most recent call last):
  File "buggy_program.py", line 10, in <module>
    buggy_loop()
  File "buggy_program.py", line 6, in buggy_loop
    print(f"The animal at index {index} is {animals[index]}")
IndexError: list index out of range
```

## Part 1: Debugging exceptions

Changing our command from ``python buggy_script.py`` to ``python -m pdb buggy_script.py`` will launch pdb and load the script. pdb will not immediately execute anything, but instead wait for your input. We assume we don't know any commands yet, so typing ``help`` is the best thing for us to start with.

```sh
> /home/willayd/buggy_program.py(1)<module>()
-> def buggy_loop():
(Pdb) help

Documented commands (type help <topic>):
========================================
EOF    c          d        h         list      q        rv       undisplay
a      cl         debug    help      ll        quit     s        unt
alias  clear      disable  ignore    longlist  r        source   until
args   commands   display  interact  n         restart  step     up
b      condition  down     j         next      return   tbreak   w
break  cont       enable   jump      p         retval   u        whatis
bt     continue   exit     l         pp        run      unalias  where

Miscellaneous help topics:
==========================
exec  pdb
```

``help <topic>`` allows you to navigate any of the items listed above. We can even input help help as a meta-command.

```sh
(Pdb) help help
h(elp)
        Without argument, print the list of available commands.
        With a command name as argument, print help about that command.
        "help pdb" shows the full pdb documentation.
        "help exec" gives help on the ! command.
```

The ``help`` we have input so far is a pdb command and not the built-in ``help`` function that Python provides. If you wanted to execute the latter, you should prefix your input with ``!``:

```sh
(Pdb) !help()

Welcome to Python 3.8's help utility!

If this is your first time using Python, you should definitely check out
the tutorial on the Internet at https://docs.python.org/3.8/tutorial/.

Enter the name of any module, keyword, or topic to get help on writing
Python programs and using Python modules.  To quit this help utility and
return to the interpreter, just type "quit".

To get a list of available modules, keywords, symbols, or topics, type
"modules", "keywords", "symbols", or "topics".  Each module also comes
with a one-line summary of what it does; to list the modules whose name
or summary contain a given string such as "spam", type "modules spam".
```

If you executed the above ``!help()`` command be sure to input q and hit enter to quit the Python interactive help.

To actually get code executing we want to ``continue``. ``help continue`` shows us more about this command.

```sh
(Pdb) help c
c(ont(inue))
        Continue execution, only stop when a breakpoint is encountered.
```

So ``c``, ``cont``, and ``continue`` would all do the same things for us. For now input ``c`` and press enter:

```sh
(Pdb) c
The animal at index 0 is dog
The animal at index 1 is cat
The animal at index 2 is turtle
Traceback (most recent call last):
  File "/usr/lib/python3.10/pdb.py", line 1726, in main
    pdb._runscript(mainpyfile)
  File "/usr/lib/python3.10/pdb.py", line 1586, in _runscript
    self.run(statement)
  File "/usr/lib/python3.10/bdb.py", line 597, in run
    exec(cmd, globals, locals)
  File "<string>", line 1, in <module>
  File "/home/willayd/buggy_program.py", line 10, in <module>
    buggy_loop()
  File "/home/willayd/buggy_program.py", line 6, in buggy_loop
    print(f"The animal at index {index} is {animals[index]}")
IndexError: list index out of range
Uncaught exception. Entering post mortem debugging
Running 'cont' or 'step' will restart the program
> /home/willayd/buggy_program.py(6)buggy_loop()
-> print(f"The animal at index {index} is {animals[index]}")
(pdb)
```

The program has executed and printed the same traceback we saw without using pdb. However, since we are running our script under pdb execution halts after an error occurs and allows us to inspect the state of the program.

``l`` (short for list) shows us where the execution halted (see -> below) and a few lines around that.

```sh
(Pdb) l
  1          def buggy_loop():
  2              animals = ["dog", "cat", "turtle"]
  3              index = 0
  4
  5              while index <= len(animals):
  6  ->              print(f"The animal at index {index} is {animals[index]}")
  7                  index += 1
  8
  9          if __name__ == "__main__":
 10              buggy_loop()
[EOF]
```

Typing ``l`` again interestingly does not give us the same result:

```sh
(Pdb) l
[EOF]
```

``list`` automatically iterates through the code every time the command is entered, and because our script is small we just reach the end-of-file. To continually display where execution halted you can enter ``l .``

```sh
(Pdb) l .
  1          def buggy_loop():
  2              animals = ["dog", "cat", "turtle"]
  3              index = 0
  4
  5              while index <= len(animals):
  6  ->              print(f"The animal at index {index} is {animals[index]}")
  7                  index += 1
  8
  9          if __name__ == "__main__":
 10              buggy_loop()
[EOF]
```

Another nice feature of pdb is that you can enter expressions see the result printed back. For instance, we know we have a variable named ``index`` in the function we are debugging, so entering that into pdb will print the value of index.

```sh
(Pdb) index
3
```

If you are debugging a longer function with a lot of variables, you may also be interested in the ``dir()`` or ``locals()`` functions. The former shows the names of all variables in the current scope; the latter gives you the names and values.

```sh
(Pdb) dir()
['animals', 'index']
(Pdb) locals()
{'animals': ['dog', 'cat', 'turtle'], 'index': 3}
```

Let us step back now and talk about the problem we are trying to solve. The traceback tells us we have an ``IndexError: list index out of range`` on line 6, and the debugger paused us at that same line. Upon inspecting the ``index`` variable in the debugger we note it has a value of 3.

Line 6 attempts to do ``animals[index]``, which fails because Python is a 0-based index language. One fix is for us to change line 5 from

```sh
while index <= len(animals):
```

to

```sh
while index < len(animals):
```

If you make that change to the source code you can enter ``restart`` into pdb to start over with the updated script logic. From there input ``c`` and you will note the script executes without issue.

```sh
(Pdb) restart
Restarting /home/willayd/buggy_program.py with arguments:

> /home/willayd/buggy_program.py(1)<module>()
-> def buggy_loop():
(Pdb) c
Post mortem debugger finished. The /home/willayd/buggy_program.py will be restarted
> /home/willayd/buggy_program.py(1)<module>()
-> def buggy_loop():
(Pdb) c
The animal at index 0 is dog
The animal at index 1 is cat
The animal at index 2 is turtle
The program finished and will be restarted
> /home/willayd/buggy_program.py(1)<module>()
-> def buggy_loop():
```

Since things are good to go now, you can type ``quit()`` into the debugger to close things out.

## Part 2: Debugging logical errors

Getting an exception in Python is a clear indicator that things are wrong, but not every bug shows up as an error. The code below is inspired by pandas bug [#49861](https://github.com/pandas-dev/pandas/issues/49861). The code as originally written used a recursive function call that was roughly equivalent to:

```python
def normalize_json(
    data,
    key_string,
    normalized_dict,
    separator
):
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{key_string}{separator}{key}"
            normalize_json(
                data=value,
                # to avoid adding the separator to the start of every key
                key_string=new_key
                if new_key[len(separator) - 1] != separator
                else new_key[len(separator) :],
                normalized_dict=normalized_dict,
                separator=separator,
            )
    else:
        normalized_dict[key_string] = data
    return normalized_dict
```

This function aims to take the keys of deeply nested dictionaries and combine them into one key with a separator. Note below how hierarchies like ``a -> b -> c`` get folded into one ``a.b.c`` key.

```python
>>> normalize_json({"a": {"b": [1, 2, 3]}}, "", {}, ".")
{'a.b': [1, 2, 3]}

>>> normalize_json({"a": {"b": {"c": [1, 2, 3]}}}, "", {}, ".")
{'a.b.c': [1, 2, 3]}
```

The OP of the pandas issue noticed that the function would incorrectly remove the start of the string at the top of the dictionary hierarchy _if_ that key began with the ``separator`` argument. For instance, if you had a key at the top of the dictionary that began with an underscore and you used an underscore separator, the very first key would get mangled. This is visible below as the normalized key is shown as ``a_b`` when it should be ``_a_b``.

```python
>>> normalize_json({"_a": {"b": [1, 2, 3]}}, "", {}, "_")
{'a_b': [1, 2, 3]}
```

To diagnose, go ahead and save the following code as ``buggy_script2.py``:

```python
def normalize_json(
    data,
    key_string,
    normalized_dict,
    separator
):
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{key_string}{separator}{key}"
            normalize_json(
                data=value,
                # to avoid adding the separator to the start of every key
                key_string=new_key
                if new_key[len(separator) - 1] != separator
                else new_key[len(separator) :],
                normalized_dict=normalized_dict,
                separator=separator,
            )
    else:
        normalized_dict[key_string] = data
    return normalized_dict


if __name__ == "__main__":
    print(normalize_json({"_a": {"b": [1, 2, 3]}}, "", {}, "_"))
```

We can start the debugger and load the script using ``python -m pdb buggy_script2.py``. However, since there is no bug this time the code will not stop unless we explicitly set a breakpoint. ``help break`` gives you some ideas on how to do this; for now start with ``break normalize_json``

```sh
> /home/willayd/buggy_script2.py(1)<module>()
-> def normalize_json(
(Pdb) break normalize_json
Breakpoint 1 at /home/willayd/buggy_script2.py:1
(Pdb) break
Num Type         Disp Enb   Where
1   breakpoint   keep yes   at /home/willayd/buggy_script2.py:1
```

Continue along by hitting ``c`` then ``l`` to list where execution paused, and you will see it is the first line of the ``normalize_json`` function.

```sh
(Pdb) c
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
(Pdb) l
  2              data,
  3              key_string,
  4              normalized_dict,
  5              separator
  6          ):
  7  ->          if isinstance(data, dict):
  8                  for key, value in data.items():
  9                      new_key = f"{key_string}{separator}{key}"
 10                      normalize_json(
 11                          data=value,
 12                          # to avoid adding the separator to the start of every key
 ```

Another command worth introducing here is ``backtrace``, or ``bt`` for short. Python functions operate as a [call stack](https://en.wikipedia.org/wiki/Call_stack), so backtrace tells you the sequence of calls that lead up to the breakpoint.

```sh
(Pdb) bt
  /usr/lib/python3.10/bdb.py(597)run()
-> exec(cmd, globals, locals)
  <string>(1)<module>()
  /home/willayd/buggy_script2.py(25)<module>()
-> normalize_json({"_a": {"b": [1, 2, 3]}}, "", {}, "_")
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
```

Within pdb the most recent call appears on the bottom (other debuggers may reverse this), so reading from the bottom up we are at ``normalize_json`` line 7 which was called by our ``buggy_script2.py`` script on line 25. The calls preceding that are internal to Python. Hit ``c`` again and another ``bt`` to see what happens next:

```sh
(Pdb) c
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
(Pdb) bt
  /usr/lib/python3.10/bdb.py(597)run()
-> exec(cmd, globals, locals)
  <string>(1)<module>()
  /home/willayd/buggy_script2.py(25)<module>()
-> normalize_json({"_a": {"b": [1, 2, 3]}}, "", {}, "_")
  /home/willayd/buggy_script2.py(10)normalize_json()
-> normalize_json(
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
```

We are in a recursive function call, so we see that ``normalize_json`` is at the bottom of our backtrace twice. This pattern would continue every time we continue script execution.

pdb let's you move up and down the stack trace. We know we are 2 ``normalize_json`` calls deep. The ``up`` and ``down`` commands not surprisingly move up and down the call stack trace, giving you the power to inspect each *frame*.

```sh
(Pdb) locals()
{'data': {'b': [1, 2, 3]}, 'key_string': '_a', 'normalized_dict': {}, 'separator': '_'}
(Pdb) up
> /home/willayd/buggy_script2.py(10)normalize_json()
-> normalize_json(
(Pdb) locals()
{'data': {'_a': {'b': [1, 2, 3]}}, 'key_string': '', 'normalized_dict': {}, 'separator': '_', 'key': '_a', 'value': {'b': [1, 2, 3]}, 'new_key': '__a'}
(Pdb) down
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
(Pdb) locals()
{'data': {'b': [1, 2, 3]}, 'key_string': '_a', 'normalized_dict': {}, 'separator': '_'}
```

The first time we called ``locals()`` we were at the most recent ``normalize_json`` call. The ``up`` command moved us back one frame; ``down`` takes us back to the current frame.

Since our input data isn't too deeply nested, we could keep continuing and moving up and down the stack to try and find where the issue appears, but this could be impractical with many layers of recursion. Fortunately we can be more intelligent with where and when we choose to pause code execution.

To do that let's ``restart`` our code execution and ``clear`` our existing breakpoint(s).

```sh
(Pdb) restart
Restarting /home/willayd/buggy_script2.py with arguments:

> /home/willayd/buggy_script2.py(1)<module>()
-> def normalize_json(
(Pdb) clear
Clear all breaks? y
Deleted breakpoint 1 at /home/willayd/buggy_script2.py:1
```

If you inspected the ``help break`` output earlier, you might have noticed that ``break`` takes an optional condition argument. This is an expression that must evaluate to ``True`` for the breakpoint to pause execution.

We know from our bug report and from inspecting some of the ``locals()`` outputs earlier that the bug likely happens when a variable named ``key_string`` has the value of ``a_b``, so we can pause execution only when that condition is met.

```sh
(Pdb) break normalize_json, key_string == "a_b"
Breakpoint 2 at /home/willayd/buggy_script2.py:1
(Pdb) c
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
(Pdb) bt
  /usr/lib/python3.10/bdb.py(597)run()
-> exec(cmd, globals, locals)
  <string>(1)<module>()
  /home/willayd/buggy_script2.py(25)<module>()
-> print(normalize_json({"_a": {"b": [1, 2, 3]}}, "", {}, "_"))
  /home/willayd/buggy_script2.py(10)normalize_json()
-> normalize_json(
  /home/willayd/buggy_script2.py(10)normalize_json()
-> normalize_json(
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
```

The above backtrace shows us pausing code execution within the third call of ``normalize_json``. Even though our breakpoint was on the ``normalize_json`` function, the expression ``key_string == "a_b"`` did not evaluate to true for the first two function calls.

Where our execution paused ``key_string`` is not modified locally, but rather received as an argument. This means the bug may surface up one call in the backtrace, so move up and inspect the code:

```sh
(Pdb) u
> /home/willayd/buggy_script2.py(10)normalize_json()
-> normalize_json(
(Pdb) ll
  1 B        def normalize_json(
  2              data,
  3              key_string,
  4              normalized_dict,
  5              separator
  6          ):
  7              if isinstance(data, dict):
  8                  for key, value in data.items():
  9                      new_key = f"{key_string}{separator}{key}"
 10  ->                  normalize_json(
 11                          data=value,
 12                          # to avoid adding the separator to the start of every key
 13                          key_string=new_key
 14                          if new_key[len(separator) - 1] != separator
 15                          else new_key[len(separator) :],
 16                          normalized_dict=normalized_dict,
 17                          separator=separator,
 18                      )
 19              else:
 20                  normalized_dict[key_string] = data
 21              return normalized_dict
(Pdb) new_key
'_a_b'
```

Our code execution paused on line 10. On line 9 ``new_key`` was assigned a value of ``_a_b``, which is what we want to see in the end result.

Look closely at line 13 however and you will note that we aren't just forwarding ``new_key`` as an argument to the next ``normalize_json`` call. Instead we have an ``if...else`` statement that determines which gets forwarded along. We can evaluate both branches of the conditional to get an idea of what is going on:

```sh
(Pdb) new_key[len(separator) - 1]
'_'
(Pdb) new_key[len(separator):]
'a_b'
(Pdb) new_key
'_a_b'
```

Our first instinct might be to simplify the function call and make the argument ``key_string=new_key``, making our buggy_script2.py script now look like:

```python
def normalize_json(
    data,
    key_string,
    normalized_dict,
    separator
):
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{key_string}{separator}{key}"
            normalize_json(
                data=value,
                # to avoid adding the separator to the start of every key
                key_string=new_key,
                normalized_dict=normalized_dict,
                separator=separator,
            )
    else:
        normalized_dict[key_string] = data
    return normalized_dict


if __name__ == "__main__":
    print(normalize_json({"_a": {"b": [1, 2, 3]}}, "", {}, "_"))
```

This reads nicer, but we have fixed one thing by breaking another. Doing a ``restart`` and ``continue`` in no longer hits our breakpoint, but the script now prints out ``{'__a_b': [1, 2, 3]}``. We want ``_a_b`` as the key not ``__a_b``.

So back to the drawing board...in pdb input ``restart`` and ``clear`` to remove the breakpoint we set so far. Enter ``break normalize_json`` so we can stop again during every function call.

```sh
(Pdb) clear
Clear all breaks? y
Deleted breakpoint 2 at /home/willayd/buggy_script2.py:1
(Pdb) break normalize_json
Breakpoint 3 at /home/willayd/buggy_script2.py:1
(Pdb)
```

Now step through a few function calls, inspect locals and see what might be happening:

```sh
(Pdb) locals()
{'data': {'_a': {'b': [1, 2, 3]}}, 'key_string': '', 'normalized_dict': {}, 'separator': '_'}
(Pdb) c
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
(Pdb) locals()
{'data': {'b': [1, 2, 3]}, 'key_string': '__a', 'normalized_dict': {}, 'separator': '_'}
(Pdb) c
> /home/willayd/buggy_script2.py(7)normalize_json()
-> if isinstance(data, dict):
(Pdb) locals()
{'data': [1, 2, 3], 'key_string': '__a_b', 'normalized_dict': {}, 'separator': '_'}
(Pdb)
```

If you look closely, you will notice that the ``key_string`` variable is already wrong on the second call to the ``normalize_json`` function. But the pattern of joining that key with one separator appears correct in the call thereafter.

A simplistic solution is to have some mechanism within our ``normalize_json`` call to know if it is the first time the function is being called or not, and special-case the handling of the first call. Inspecting ``locals()`` across the different function calls, we notice in the first call that ``key_string`` is an empty string but has a value in all subsequent calls. Knowing this we can set up a condition to only strip leading separators if we are NOT in the first function call.

```python
def normalize_json(
    data,
    key_string,
    normalized_dict,
    separator
):
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{key_string}{separator}{key}"
            if not key_string:
                new_key = new_key.removeprefix(separator)
            normalize_json(
                data=value,
                # to avoid adding the separator to the start of every key
                key_string=new_key,
                normalized_dict=normalized_dict,
                separator=separator,
            )
    else:
        normalized_dict[key_string] = data
    return normalized_dict


if __name__ == "__main__":
    print(normalize_json({"_a": {"b": [1, 2, 3]}}, "", {}, "_"))
```

To verify this now works, ``restart`` the program, ``clear`` any breakpoint(s) and ``continue`` to let things run. You should now get the right answer.

```sh
(Pdb) restart
Restarting /home/willayd/buggy_script2.py with arguments:

> /home/willayd/buggy_script2.py(1)<module>()
-> def normalize_json(
(Pdb) clear
Clear all breaks? y
Deleted breakpoint 3 at /home/willayd/buggy_script2.py:1
(Pdb) c
{'_a_b': [1, 2, 3]}
The program finished and will be restarted
```

## Closing Thoughts

If you have made it this far congratulations! With modern visual debuggers integrated into IDEs, the way of debugging illustrated above may not be the most commonplace. However, through liberal use of the ``help`` command you may find that ``pdb`` has many features that are not implemented or obvious to use in higher level debuggers. Barring some differences, you'll also find that this method of using ``pdb`` translates well into using ``gdb`` and extensions like the Cython debugger, which will be represented in future blog posts.
