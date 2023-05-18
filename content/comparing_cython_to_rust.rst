*******************************************************
Comparing Cython to Rust - Evaluating Python Extensions
*******************************************************

:date: 2023-05-17
:category: performance
:tags: python, cython
:author: Will Ayd
:description: Cython is a tool for Python developers to make low level programming easier. Rust is a language that thinks "Systems Programmers Can Have Nice Things". How do they compare?
:summary: Here we will see how a Python developer can consider Rust as a viable alternative to Cython. Rust abstracts a lot of the same things that Cython does, albeit it with a different architecture and syntax. Though a truly apples-to-apples comparison is difficult, this article will show you just how well it compares.
:image: https://willayd.com/images/og_logo.png

`Rust <https://www.rust-lang.org/>`_ as a language has had tremendous growth in recent years. With no intention of starting a language war, Rust has a much stronger type checking system than a language like C, and arguably feels more approachable than a language like C++. It also includes thread safety as part of the language, which can be immensely useful for those looking to optimize their system.

Rust is also growing in usage as an extension language for Python. `PyO3 <https://github.com/PyO3/pyo3>`_ makes writing extensions relatively easy, especially when compared to the same toolchain(s) for C/C++ extensions. While not as "Pythonic" as Cython, you can argue that Rust is more approachable to Python-developers than C/C++ are as languages. To see it in action, let's compare a Cython written extension to a Rust-written extension.

For demonstration purposes we are taking a trivial example of a custom-implemented ``max`` function along the columns of a NumPy array. The example is admittely naive (NumPy natively can handle this), but as a developer you may find yourself following a similar pattern for custom algorithms.

Coding the example in Cython
----------------------------

Here is our ``find_max`` function with a relatively optimized Cython implementation. Within a ``cdef`` function, we determine the bounds of a 2D int64 array, loop over the columns / rows and evaluate each member of the array, looking for the largest value in each column.

.. code-block:: python

   cimport cython
   from libc.limits cimport LLONG_MIN
   import numpy as np
   from numpy cimport ndarray, int64_t
   import time

   @cython.boundscheck(False)
   @cython.wraparound(False)
   cdef ndarray[int64_t, ndim=1] _find_max(ndarray[int64_t, ndim=2] values):
       cdef:
           ndarray[int64_t, ndim=1] out
           int64_t val, colnum, rownum

       N, K = (<object>values).shape
       out = np.zeros(K, dtype=np.int64)
       for colnum in range(K):
           val = LLONG_MIN  # imperfect assumption, but no INT64_T_MIN from numpy
           for rownum in range(N):
               if val <= values[rownum, colnum]:
                   val = values[rownum, colnum]

           out[colnum] = val

       return out


   def find_max(ndarray[int64_t, ndim=2] values):
       cdef ndarray[int64_t, ndim=1] result
       start = time.time_ns()
       result = _find_max(values)
       end = time.time_ns()
       duration = (end - start) / 1_000_000
       print(f"cypy took {duration} milliseconds")
       return result

For brevity I won't be listing out the instructions to cythonize and build a shared library, but if you need you can follow similar instructions from the previous article on `debugging Cython extensions with gdb <{filename}/debugging_cython_extensions.rst>`_. For this article, assume that this gets built to a shared library named `cypy`.


Building the same in Rust
-------------------------

PyO3 will be our tool for setting up Rust <> Python interoperability. Per their `documentation on building modules <https://pyo3.rs/v0.18.3/module>`_ we could choose to build manually or use `maturin <https://github.com/PyO3/maturin>`_. For ease of demonstration we will use the latter.

.. code-block:: sh

   >>> maturin new rustpy
   >>> cd rustpy

Within our newly created project, add ``numpy == "0.18"`` to the dependencies section. This will let us use the `rust-numpy <https://github.com/PyO3/rust-numpy>`_ crate to pass numpy arrows between Python and Rust. Afterwards, open `lib.rs` an insert the following code:

.. code-block:: rust

   use numpy::ndarray::{Array1, ArrayView2, Axis};
   use numpy::{PyArray1, PyReadonlyArray2};
   use pyo3::{pymodule, types::PyModule, PyResult, Python};
   use std::time::SystemTime;

   #[pymodule]
   #[pyo3(name = "rustpy")]
   fn rust_ext(_py: Python<'_>, m: &PyModule) -> PyResult<()> {
       fn find_max(arr: ArrayView2<'_, i64>) -> Array1<i64> {
           let mut out = Array1::default(arr.ncols());

           for (i, col) in arr.axis_iter(Axis(1)).enumerate() {
               let mut val = i64::MIN;
               for x in col {
                   if val <= *x {
                       val = *x;
                   }
               }

               out[i] = val;
           }

           out
       }

       #[pyfn(m)]
       #[pyo3(name = "find_max")]
       fn find_max_py<'py>(py: Python<'py>, x: PyReadonlyArray2<'_, i64>) -> &'py PyArray1<i64> {
           let start = SystemTime::now();
           let result = find_max(x.as_array()).into_pyarray(py);
           let end = SystemTime::now();
           let duration = end.duration_since(start).unwrap();
           println!("rustpy took {} milliseconds", duration.as_millis());
           result
       }

       Ok(())
   }

Studying the above closely, the ``find_max_py`` function is the bridge between Rust and Python, and it ultimately dispatches to the ``find_max`` function. That function accepts a 2 dimensional view of an array, and returns a newly created 1D array full of 64 bit integers. Within the function body, you see the dynamic creation of the return value, as well as iteration by column. While the semantics vary, you should see that this follows the same general outline as our Cython implementation.

With this in place, run ``maturin develop --release`` from the project root. This will take care of installing the local source code into a Python package with optimizations.

Comparing Results
-----------------

Both implementations above include not-very-scientific timers to give us an idea of general performance. Let's set up with the following code:

.. code-block:: python

   >>> import numpy as np
   >>> np.random.seed(42)
   >>> arr = np.random.randint(100_000, size=(100, 1_000_000))

Let's check our cypy performance:

.. code-block:: python

   >>> import cypy
   >>> result1 = cypy.find_max(arr)
   cypy took 289.319301 milliseconds

Versus the same function implemented in Rust:

.. code-block:: python

   >>> import rustpy
   >>> result2 = rustpy.find_max(arr)
   rustpy took 116 milliseconds
   >>> (result1 == result2).all()
   True

The rust implementation only took ~40% of the time - not bad!

Parallelization
---------------

Another area where Rust extensions can really shine is in parallelization, due to the aforementioned language guarantees of thread safety. Cython offers `parallelization <https://cython.readthedocs.io/en/latest/src/userguide/parallelism.html>`_ using OpenMP, but as `I recently discovered <https://github.com/pandas-dev/pandas/pull/53149>`_ there are quite a few downsides to that when it comes to packaging, usability and cross-platform behavior.

Since Rust handles this more natively, let's see how it would tackle the above code but in a parallel way. For this purpose we are going to use the `rayon <https://docs.rs/rayon/latest/rayon/>`_ feature that comes bundled with the `Rust ndarray crate <https://docs.rs/ndarray/latest/ndarray/>`_. To enable that, go ahead and add ``ndarray = {version = "0.15", features=["rayon"]}`` to your dependencies in `Cargo.toml`.

Afterwards we are going to add 2 new functions to our `rustpy` library - one to handle the internals and the other to serve as the bridge to Python. For starters, let us update the imports at the top of our module:

.. code-block:: rust

   use ndarray::parallel::prelude::*;
   use numpy::ndarray::{Array1, ArrayView2, Axis, Zip};
   use numpy::{IntoPyArray, PyArray1, PyReadonlyArray2};
   use pyo3::{pymodule, types::PyModule, PyResult, Python};
   use std::sync::{Arc, Mutex};
   use std::time::SystemTime;

Then go ahead and all the following code below the ``find_max_py`` function.

.. code-block:: rust

       fn find_max_parallel(arr: ArrayView2<'_, i64>) -> Array1<i64> {
           let mutex = Arc::new(Mutex::new(Array1::default(arr.ncols())));

           // parallel iterator is not implemented, so some hacks
           // https://github.com/rust-ndarray/ndarray/issues/1043
           // https://github.com/rust-ndarray/ndarray/issues/1093
           Zip::indexed(arr.axis_iter(Axis(1)))
               .into_par_iter()
               .for_each(|(i, col)| {
                   let mut val = i64::MIN;
                   for x in col {
                       if val <= *x {
                           val = *x;
                       }
                   }

                   let mut guard = mutex.lock().unwrap();
                   guard[i] = val;
               });

           // https://stackoverflow.com/questions/29177449/how-to-take-ownership-of-t-from-arcmutext
           let lock = Arc::try_unwrap(mutex).expect("Lock still have multiple owners");
           lock.into_inner().expect("Mutex cannot be locked")
       }

       // wrapper of `find_max`
       #[pyfn(m)]
       #[pyo3(name = "find_max_parallel")]
       fn find_max_py_parallel<'py>(
           py: Python<'py>,
           x: PyReadonlyArray2<'_, i64>,
       ) -> &'py PyArray1<i64> {
           let start = SystemTime::now();
           let result = find_max_parallel(x.as_array()).into_pyarray(py);
           let end = SystemTime::now();
           let duration = end.duration_since(start).unwrap();
           println!("rustpy parallel took {} milliseconds", duration.as_millis());
           result
       }


Within the comments I've linked some StackOverflow articles that you may find of interest. At a high level, now that we want to execute things in parallel we need to implement a `Mutex <https://doc.rust-lang.org/std/sync/struct.Mutex.html>`_ to prevent data races. We also use an automatic reference counter `Arc <https://doc.rust-lang.org/std/sync/struct.Arc.html>`_, which is a common way for sharing things across thread.

So how does this compare performance-wise to our examples above?

.. code-block:: python

   >>> import rustpy
   >>> result3 = rustpy.find_max_parallel(arr)
   rustpy took 234 milliseconds
   >>> (result2 == result3).all()
   True

We get the same results which is great, but compared to the non-parallel implementation we are now slower - almost twice as slow. What gives?!?

Without peering into every detail, it goes without saying that there is "no such thing as a free lunch". Using the mutex to synchronize parallel code above is no exception, and likely the cost of that synchronization far exceeds the benefit of it. Keep in mind that we are dealing with an array of 100 x 1_000_000 and attempting to synchronize a thread per column. That's a lot of threads to operate on rows of 100 records!

What happens if we transpose the array?

.. code-block:: python

   >>> arr2 = arr.T
   >>> arr2.shape
   (1000000, 100)
   >>> rustpy.find_max(arr2)
   rustpy took 67 milliseconds
   >>> rustpy.find_max_parallel(arr2)
   rustpy took 38 milliseconds

That's more like it! Whereas before we created 1_000_000 threads to operate on arrays of 100 records, now we use 100 threads to operate on arrays of 1_000_000 records. The relative cost of starting / stopping threads and synchronizing access via the mutex in this case is far lower than the relative performance gain we get from allowing threads to operate on large arrays in parallel.

Closing Thoughts
----------------

From my initial trials I was very surprised by how good Rust was for building extensions. The language itself is pretty natural in a way that I think could be useful to higher-level programmers, while offering great performance at the same time. Not pictured in the above analysis were a ton of mistakes in trying to get code parallelized via Rust. In C/C++ I likely would have made a very buggy program; the Rust compiler prevented me from doing so here. In all, I think Rust can creep into the same realm that Cython occupies today and become a serious competitor for easy extension authoring.
