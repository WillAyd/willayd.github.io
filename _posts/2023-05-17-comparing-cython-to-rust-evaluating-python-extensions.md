---
title: "Comparing Cython to Rust - Evaluating Python Extensions"
date: 2023-05-17T00:00:00
categories:
  - performance
tags:
  - python
  - rust
# cSpell:ignore Cython pythonic cimport cython libc LLONG numpy cython cdef ndarray ndim colnum rownum ssize dtype cypy rustpy millis maturin randint pymodule ncols pyfn println Lustig uout usize Repr Ryhl boundscheck Goldblum cythonize pyarrow struct uget pyarray
---

[Rust](https://www.rust-lang.org/) as a language has had tremendous growth in recent years. With no intention of starting a language war, Rust has a much stronger type checking system than a language like C, and arguably feels more approachable than a language like C++. It also includes thread safety as part of the language, which can be immensely useful for those looking to optimize their system.

Rust is also growing in usage as an extension language for Python. [PyO3](https://github.com/PyO3/pyo3) makes writing extensions relatively easy, especially when compared to the same toolchain(s) for C/C++ extensions. While not as "pythonic" as Cython, you can argue that Rust is more approachable to Python-developers than C/C++ are as languages. To see it in action, let's compare a Cython written extension to a Rust-written extension.

For demonstration purposes we are taking a trivial example of a custom-implemented ``max`` function along the columns of a NumPy array. The example is admittedly naive (NumPy natively can handle this), but as a developer you may find yourself following a similar pattern for custom algorithms.

The source code for these exercises is available on my [GitHub](https://github.com/WillAyd/rustpy).

## Coding the example in Cython

Here is our ``find_max`` function with a relatively optimized Cython implementation. Within a ``cdef`` function, we determine the bounds of a 2D int64 array, loop over the columns / rows and evaluate each member of the array, looking for the largest value in each column.

```python
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
        int64_t val, colnum, rownum, new_val
        Py_ssize_t N, K

    N, K = (<object>values).shape
    out = np.zeros(K, dtype=np.int64)
    for colnum in range(K):
        val = LLONG_MIN  # imperfect assumption, but no INT64_T_MIN from numpy
        for rownum in range(N):
            new_val = values[rownum, colnum]
            if val < new_val:
                val = new_val

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
```

For brevity I won't be listing out the instructions to cythonize and build a shared library, but if you need you can follow similar instructions from the previous article on [debugging Cython extensions with gdb]({% post_url 2023-03-10-fundamental-python-debugging-part-3-cython-extensions %}). For this article, assume that this gets built to a shared library named ``cypy``.

## Building the same in Rust

PyO3 will be our tool for setting up Rust <> Python interoperability. Per their [documentation on building modules](https://pyo3.rs/v0.18.3/module) we could choose to build manually or use [maturin](https://github.com/PyO3/maturin). For ease of demonstration we will use the latter.

```sh
$ maturin new rustpy
$ cd rustpy
```

Within our newly created project, add ``numpy == "0.18"`` to the dependencies section. This will let us use the [rust-numpy](https://github.com/PyO3/rust-numpy) crate to pass numpy arrows between Python and Rust. Afterwards, open ``lib.rs`` an insert the following code:

```rs
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
                if val < *x {
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
```

Studying the above closely, the ``find_max_py`` function is the bridge between Rust and Python, and it ultimately dispatches to the ``find_max`` function. That function accepts a 2 dimensional view of an array, and returns a newly created 1D array full of 64 bit integers. Within the function body, you see the dynamic creation of the return value, as well as iteration by column. While the semantics vary, you should see that this follows the same general outline as our Cython implementation.

With this in place, run ``maturin develop --release`` from the project root. This will take care of installing the local source code into a Python package with optimizations.

## Comparing Results

Both implementations above include not-very-scientific timers to give us an idea of general performance. Let's set up with the following code:

```python
>>> import numpy as np
>>> np.random.seed(42)
>>> arr = np.random.randint(100_000, size=(100, 1_000_000))
```

Let's check our cypy performance:

```python
>>> import cypy
>>> result1 = cypy.find_max(arr)
cypy took 273.319301 milliseconds
```

Versus the same function implemented in Rust:

```python
>>> import rustpy
>>> result2 = rustpy.find_max(arr)
rustpy took 116 milliseconds
>>> (result1 == result2).all()
True
```

The rust implementation only took ~45% of the time - not bad!

## Parallelization

Another area where Rust extensions can really shine is in parallelization, due to the aforementioned language guarantees of thread safety. Cython offers [parallelization](https://cython.readthedocs.io/en/latest/src/userguide/parallelism.html) using OpenMP, but as [I recently discovered](https://github.com/pandas-dev/pandas/pull/53149) there are quite a few downsides to that when it comes to packaging, usability and cross-platform behavior.

Since Rust handles this more natively, let's see how it would tackle the above code but in a parallel way. For this purpose we are going to use the [rayon](https://docs.rs/rayon/latest/rayon/) feature that comes bundled with the [Rust ndarray crate](https://docs.rs/ndarray/latest/ndarray/). To enable that, go ahead and add ``ndarray = {version = "0.15", features=["rayon"]}`` to your dependencies in Cargo.toml.

Afterwards we are going to add 2 new functions to our rustpy library - one to handle the internals and the other to serve as the bridge to Python. For starters, let us update the imports at the top of our module:

```rs
use ndarray::parallel::prelude::*;
use numpy::ndarray::{Array1, ArrayView2, Axis, Zip};
use numpy::{IntoPyArray, PyArray1, PyReadonlyArray2};
use pyo3::{pymodule, types::PyModule, PyResult, Python};
use std::sync::{Arc, Mutex};
use std::time::SystemTime;
```

Then go ahead and all the following code below the ``find_max_py`` function.

```rs
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
                if val < *x {
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
```

Within the comments I've linked some StackOverflow articles that you may find of interest. At a high level, now that we want to execute things in parallel we need to implement a [Mutex](https://doc.rust-lang.org/std/sync/struct.Mutex.html) to prevent data races. We also use a thread-safe reference counter [Arc](https://doc.rust-lang.org/std/sync/struct.Arc.html); using these in tandem is a common pattern in Rust.

So how does this compare performance-wise to our examples above?

```rs
>>> import rustpy
>>> result3 = rustpy.find_max_parallel(arr)
rustpy parallel took 234 milliseconds
>>> (result2 == result3).all()
True
```

We get the same results which is great, but compared to the non-parallel implementation we are now slower - almost twice as slow. What gives?!?

Without peering into every detail, it goes without saying that there is "no such thing as a free lunch". Using the mutex to synchronize parallel code above is no exception, and likely the cost of that synchronization far exceeds the benefit of it. Keep in mind that we are dealing with an array of 100 x 1_000_000 and attempting to synchronize a thread per column. That's a lot of threads to operate on rows of 100 records!

What happens if we transpose the array?

```rs
>>> arr2 = arr.T
>>> arr2.shape
(1000000, 100)
>>> rustpy.find_max(arr2)
rustpy took 67 milliseconds
>>> rustpy.find_max_parallel(arr2)
rustpy parallel took 38 milliseconds
```

That's more like it! Whereas before we created 1_000_000 threads to operate on arrays of 100 records, now we use 100 threads to operate on arrays of 1_000_000 records. The relative cost of starting / stopping threads and synchronizing access via the mutex in this case is far lower than the relative performance gain we get from allowing threads to operate on large arrays in parallel.

## Even Faster Parallelization

[Irv Lustig](https://github.com/Dr-Irv) had an idea that we could do away with the mutex, which would reduce the parallelization overhead of synchronizing access to the ``out`` variable. Internally the NumPy array manages its data in a contiguous array of memory, and indexing methods like ``out[i]`` just points to a location in memory that is ``i`` steps away from the start of that array. Because each thread manages its own value of ``i``, each thread also writes to a unique memory location without any overlap. Careful attention paid to this fact makes the synchronization unnecessary.

Rust by default is skeptical of this, so we have to jump through a few hoops to make it work. Stepwise the first thing we wanted to do was get rid of the Mutex. However, Rust will reject the following code:

```rs
let mut out = Array1::default(arr.ncols());

Zip::indexed(arr.axis_iter(Axis(1)))
    .into_par_iter()
    .for_each(|(i, col)| {
        let mut val = i64::MIN;
        for x in col {
            if val < *x {
                val = *x;
            }
        }

        out[i] = val;
    });
out
```

With the following error

```sh
error[E0596]: cannot borrow `out` as mutable, as it is a captured variable in a `Fn` closure
```

As explained in [this link](https://users.rust-lang.org/t/cannot-borrow-write-as-mutable-as-it-is-a-captured-variable-in-a-fn-closure/78560) the closure cannot use a mutable reference (here the ``out`` variable) defined outside of its scope. To make this possible we use the [UnsafeCell](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html) primitive. Our first attempt to do so could look something like this:

```rs
let mut out = Array1::default(arr.ncols());
let uout = UnsafeCell::new(&mut out);

...
// Let's assume we are within the closure
   (*uout.get())[i] = val;
});

out
```

Alas things aren't so simple. This will in turn yield another error

```rs
error[E0277]: `UnsafeCell<&mut ArrayBase<OwnedRepr<i64>, Dim<[usize; 1]>>>` cannot be shared between threads safely

...

 = help: within `[closure@src/lib.rs:56:23: 56:33]`, the trait `Sync` is not implemented for `UnsafeCell<&mut ArrayBase<OwnedRepr<i64>, Dim<[usize; 1]>>>`
```

If you look carefully the note that the trait ``Sync is not implemented...`` means Rust isn't happy we are trying to use that object across threads without the ``Sync`` trait being implemented on it. Some research will take us to the [SyncUnsafeCell](https://doc.rust-lang.org/std/cell/struct.SyncUnsafeCell.html). This object implements the ``Sync`` trait, but as of writing is only available in nightly builds. While it is something to track, it does not help us today.

To work around this, user [Alice Ryhl](https://stackoverflow.com/users/1704411/alice-ryhl) over at StackOverflow came up with [this nifty solution](https://stackoverflow.com/a/65182786/621736). Alice's code works generically for slices; the implementation we have specializes only to ``Array1<i64>`` types, but keeps the same structure in place.

At a high level, instead of using the ``UnsafeCell`` directly, we create our own structure that uses the ``UnsafeCell`` as a field member. The custom structure provides blank trait implementations for ``Send`` and ``Sync`` so the compiler is happy to let it work across threads. With that in place, we can call the ``write`` member function from within our threads.

```rs
// https://stackoverflow.com/questions/65178245/how-do-i-write-to-a-mutable-slice-from-multiple-threads-at-arbitrary-indexes-wit
#[derive(Copy, Clone)]
struct UnsafeArray1<'a> {
    array: &'a UnsafeCell<Array1<i64>>,
}

unsafe impl<'a> Send for UnsafeArray1<'a> {}
unsafe impl<'a> Sync for UnsafeArray1<'a> {}

impl<'a> UnsafeArray1<'a> {
    pub fn new(array: &'a mut Array1<i64>) -> Self {
        let ptr = array as *mut Array1<i64> as *const UnsafeCell<Array1<i64>>;
        Self {
            array: unsafe { &*ptr },
        }
    }

    /// SAFETY: It is UB if two threads write to the same index without
    /// synchronization.
    pub unsafe fn write(&self, i: usize, value: i64) {
        let ptr = self.array.get();
        (*ptr)[i] = value;
    }
}

fn find_max_unsafe(arr: ArrayView2<'_, i64>) -> Array1<i64> {
    let mut out = Array1::default(arr.ncols());
    let uout = UnsafeArray1::new(&mut out);

    Zip::indexed(arr.axis_iter(Axis(1)))
        .into_par_iter()
        .for_each(|(i, col)| {
            let mut val = i64::MIN;
            for x in col {
                if val < *x {
                    val = *x;
                }
            }

            unsafe { uout.write(i, val) };
        });

    out
}

#[pyfn(m)]
#[pyo3(name = "find_max_unsafe")]
fn find_max_py_unsafe<'py>(py: Python<'py>, x: PyReadonlyArray2<'_, i64>) -> &'py PyArray1<i64> {
    let start = SystemTime::now();
    let result = find_max_unsafe(x.as_array()).into_pyarray(py);
    let end = SystemTime::now();
    let duration = end.duration_since(start).unwrap();
    println!("rustpy unsafe took {} milliseconds", duration.as_millis());
    result
}
```

## Turning off bounds checking

Since we are running ``unsafe`` code blocks, we also have the ability to disable bounds checking our arrays. In Cython you would typically do this with the ``@cython boundscheck(False)`` decorator. With the [ndarray rust crate](https://docs.rs/ndarray/latest/ndarray/) you would replace the index operator ``[]`` with [uget](https://docs.rs/ndarray/latest/ndarray/struct.ArrayBase.html#method.uget) or [uget_mut](https://docs.rs/ndarray/latest/ndarray/struct.ArrayBase.html#method.uget_mut). For us, this means changing our write implementation for the ``UnsafeArray1`` class to:

```rs
pub unsafe fn write(&self, i: usize, value: i64) {
    let ptr = self.array.get();
    *(*ptr).uget_mut(i) = value;
}
```

So how does this compare function wise?

```python
>>> res1 = cypy.find_max(arr)
cypy took 284.153331 milliseconds
>>> res2 = rustpy.find_max(arr)
rustpy took 113 milliseconds
>>> res3 = rustpy.find_max_parallel(arr)
rustpy parallel took 223 milliseconds
>>> res4 = rustpy.find_max_unsafe(arr)
rustpy unsafe took 47 milliseconds
>>> ((res1 == res2) & (res1 == res3) & (res1 == res4)).all()
True
```

Compared to our initial Cython implementation, our unsafe threaded implementation takes about 16.5% of the same runtime. Not bad.

The benchmarks above were recorded on a Lemur Pro laptop with a 12th Gen Intel(R) Core(TM) i7-1255U processor and 12 logical cores. Results will vary depending on your hardware and OS. If you want more control over the degree of parallelization than that which comes out of the box, be advised that this all dispatches to [rayon](https://docs.rs/rayon/latest/rayon/) under the hood. Rayon uses [one thread per CPU](https://github.com/rayon-rs/rayon/blob/master/FAQ.md#how-many-threads-will-rayon-spawn) by default. You could accept an argument into your extension function that limits the number of threads being spawned at one time, or alternately you can set the ``RAYON_NUM_THREADS`` environment variable.

From my machine if I run ``RAYON_NUM_THREADS=2 python`` and within the interpreter execute ``rustpy.find_max_parallel(arr)``, I get the response that ``rustpy parallel took 71 seconds``. This is an improvement over the default parallel implementation, which as we noted in the previous section introduced a lot of overhead with thread synchronization when arrays had a large number of columns and a relatively small amount of rows.

## Closing Thoughts

From my initial trials I was very surprised by how good Rust was for building extensions. The language itself is pretty natural in a way that I think could be useful to higher-level programmers, while offering great performance at the same time. Not pictured in the above analysis were a ton of mistakes in trying to get code parallelized via Rust. In C/C++ I likely would have made a very buggy program; the Rust compiler prevented me from doing so here. In all, I think Rust can creep into the same realm that Cython occupies today and become a serious competitor for easy extension authoring.

I also want to mention [Irv Lustig](https://github.com/Dr-Irv), [Brock Mendel](https://github.com/jbrockmendel), [Marc Garcia](https://github.com/datapythonista) and [Nathan Goldblum](https://github.com/ngoldbaum) for their help in implementing and improving this article. Thanks all for your help and support!
