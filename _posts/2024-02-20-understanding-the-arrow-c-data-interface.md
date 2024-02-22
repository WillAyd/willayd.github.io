---
title: "Understanding the Arrow C Data Interface"
date: 2024-02-20T00:00:00
description: This blog post describes how the Arrow C Data interface works, as witnessed through transformation of the pantab library.
categories:
  - arrow
tags:
  - python
  - arrow
# cSpell:ignore pantab BITMASK BYTEMASK nanoarrow pyarrow pydict adbc ADBC Joris Bossche bitmasks itertuples
---

The [Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html) is an amazing tool, and while it documents its own potential use cases I wanted to dedicate a blog post to my personal experience using it.

## Problem Statement

Transferring data across systems and libraries is difficult and time-consuming. This statement applies not only to compute time but perhaps more importantly to developer time as well.

I first ran into this issue over 5 years ago when I started a library called [pantab](https://pantab.readthedocs.io/en/latest/). At the time, I had just become a core developer of [pandas](https://pandas.pydata.org/), and through consulting work had been dealing a lot with [Tableau](https://www.tableau.com/). Tableau had at that time just released their [Hyper API](https://www.tableau.com/developer/learning/tableau-hyper-api), which is a way to exchange data to/from their proprietary Hyper database.

*Great...*, I said to myself, *I know a lot of pandas internals and I think writing a DataFrame to a Hyper database will be easier than any other option*. Hence, pantab was created.

As you may or may not already be aware, most high-performance Python libraries in the analytics space get their performance from implementing parts of their code base in *lower-level* languages like C/C++/Rust. So with pantab I set out to do the same thing. The problem, however, is that pandas did NOT expose any of its internal data structures to other libraries. As such, pantab hacked a lot of things to make this integration "work", but in a way that was very fragile across pandas releases and would not be able to garner any support.

Late in 2023 I decided that pantab was due for a rewrite. Hacking into the pandas internals was not going to work any more, especially as the number of data types that pandas supported started to grow. What pantab needed was an agreement with a library like pandas as to how to exchange low-level data at an extremely high level of performance.

Fortunately, I wasn't the only person with that idea. Data interchange libraries that weren't even a thought when pantab started were now a reality, so it was time to test those out.

## Status Quo

When it was first created, pantab used used [pandas.DataFrame.itertuples](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.itertuples.html) to loop over every row and every element within a DataFrame before writing it out to a Hyper file. While this worked and was faster than what most users would write by hand, it still really wasn't that fast. By looping in Python and using tuples, every value in the DataFrame would be converted to a Python object.

A later version of pantab which required a minimum of pandas 1.3 ended up hacking into the internals of pandas, calling something like ``df._mgr.column_arrays`` to get a ``NumPy`` array for each column in the DataFrame. Combined with the [NumPy Array Iterator API](https://numpy.org/doc/stable/reference/c-api/iterator.html), pantab could iterate over raw NumPy arrays instead of doing a loop in Python. This helped a lot with performance, and while the NumPy Array Iterator API was solid, the pandas internals [would change across releases](https://github.com/innobi/pantab/issues/190).

And so far we have just talked about writing. When it comes to reading, pantab would simply build up a Python array of PyObjects and try to convert to more appropriate data types after all data was read. A more efficient reader probably could have been built for primitive types like integers and floats to write to a buffer directly and create a NumPy array from that buffer, but string data *had* to be an array of Python objects. Given that limitation, I didn't even bother trying to do much here.

## Attempt 1: Python DataFrame Interchange Protocol

Before I ever considered the Arrow C Data Interface, my first attempt at getting high performance and easy data exchange from pandas to Hyper was through the [Python DataFrame interchange protocol](https://data-apis.org/dataframe-protocol/latest/purpose_and_scope.html). While initially promising, this soon became very problematic.

For starters, *Memory ownership and lifetime* is listed as something in scope of the protocol, but the protocol defines nothing in particular about lifetimes, copy / move semantics, or related memory-management concepts. Without this, writing extensions that consume the interface becomes very difficult. While writing pantab I found out the hard way that buffers exported from pandas for primitive types like ``int`` and ``float`` had a different lifetime than ``string`` data. While that is an unfortunate implementation detail, I could not find anything in the protocol itself to offer guidance on that topic.

Another major issue for the interchange protocol is that *Non-Python API standardization (e.g., C/C++ APIs)* is explicitly a non-goal. While the protocol specifies how libraries should *export* raw data, libraries that want to *consume* this data end up needing to roll their own code for ingesting the raw data (by contrast, the Arrow C Data Interface offers [nanoarrow](https://arrow.apache.org/nanoarrow/latest/index.html) for this purpose). In effect, this made consuming data through this interchange a huge effort.

The way the DataFrame Interchange Protocol decided to handle nullability is an area where trying to be inclusive of many different strategies ended up as a detriment to all. Here's the enum the protocol specified:

```python
class ColumnNullType(enum.IntEnum):
    """
    Integer enum for null type representation.

    Attributes
    ----------
    NON_NULLABLE : int
        Non-nullable column.
    USE_NAN : int
        Use explicit float NaN value.
    USE_SENTINEL : int
        Sentinel value besides NaN.
    USE_BITMASK : int
        The bit is set/unset representing a null on a certain position.
    USE_BYTEMASK : int
        The byte is set/unset representing a null on a certain position.
    """

    NON_NULLABLE = 0
    USE_NAN = 1
    USE_SENTINEL = 2
    USE_BITMASK = 3
    USE_BYTEMASK = 4
```

Requiring developers to integrate potentially all of these methods across any type they may consume is a lot of effort. And in the case of ``USE_SENTINEL`` there is nothing in the specification for how to actually get that sentinel. All in all, this requires jumping through a lot of hoops just to figure out if a record is missing or not.

Another limitation with the DataFrame Interchange Protocol is the fact that it only really talks about how to consume data, but offers no guidance on how to produce it. If starting from your extension, you have no tools or library to manually build buffers. And for downstream libraries, there is no canonical way to then consume a buffer through the protocol. In the case of pantab, this meant that I could use the protocol to *read* pandas data and then *write* to a Hyper database, but going in the other direction I was out of luck.

Finally, and related to all of the issues above, the pandas implementation of the DataFrame Interchange Protocol left a lot to be desired. While started with good intentions, it never quite got the development effort needed to make it really effective. I already mentioned the lifetime issues across various data types, but nullability handling was all over the place across types. Metadata was often passed along incorrectly from pandas down through the interface...essentially making it a very high effort for consumers to try and use it.

## Arrow C Data Interface to the Rescue

After stumbling around the DataFrame Protocol Interface for a few weeks, [Joris Van den Bossche](https://jorisvandenbossche.github.io/pages/about.html) asked me why I didn't look at the [Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html). The answer of course was that I was just not very familiar with it. Joris knows a ton about pandas and Arrow, so I figured it best to take his word for it and try it out.

Almost immediately my issues went away. To wit:

  1. Memory ownership and lifetime - this is [well defined](https://arrow.apache.org/docs/format/CDataInterface.html#memory-management) at low levels
  2. API standardization - this is achieved via [nanoarrow](https://arrow.apache.org/nanoarrow/latest/index.html)
  3. Nullability handling - this follows the Arrow format exclusively, which uses bitmasks
  4. Constructing buffers from an extension - nanoarrow lets you create and not just read Arrow structures
  5. pandas implementation - pandas uses the [PyCapsule interface](https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html#arrowstream-export) to transfer data

This represented a significant times saving. With well defined memory semantics, a low-level API and clean nullability handling the amount of extension code I had to write was drastically reduced. I felt more confident in the implementation and had to deal with less memory corruption / crashes than before.

Without going too deep in the benchmarks game, the Arrow C Data Interface implementation yielded a 25% performance improvement for me when writing strings. When reading data, it was more like a 500% improvement than what had been previously implemented. Not bad...

On top of those improvements, I was able to implement *more data types* given the richness of the Arrow type system. And perhaps most importantly, my code is no longer tied to the fragile internals of one library. The Arrow C Data Interface is guaranteed to be stable, meaning less surprises for me as a developer in the future.

## Bonus Feature - Bring Your Own Library

While it wasn't explicitly my goal at the outset, implementing the Arrow C Data Interface had the benefit of decoupling a dependency on pandas. While pandas was the de facto library when pantab was first written, many other Arrow-based libraries have popped up since then and grown a large following. By using the Arrow C Data Interface, pantab was able to achieve a *bring your own DataFrame library mentality*. Ignoring some slight differences in how far each library goes to support the Arrow specification, users can now with pantab perform all of the following calls and get equivalent results.

```python
>>> import pantab as pt
>>> import pantab as pd
>>> df = pd.DataFrame({"col": [1, 2, 3]})
>>> pt.frame_to_hyper(df, "example.hyper", table="test")

>>> import polars as pl
>>> df = pl.DataFrame({"col": [1, 2, 3]})
>>> pt.frame_to_hyper(df, "example.hyper", table="test")

>>> import pyarrow as pa
>>> tbl = pa.Table.from_pydict({"col": [1, 2, 3]})
>>> pt.frame_to_hyper(tbl, "example.hyper", table="test")
```

While these all produce the same results, as the author of pantab I did not have to do anything extra to accommodate polars versus pandas versus pyarrow. The Arrow C Data Interface takes care of all of that not just for these libraries, but for any other DataFrame library that chooses to implement the interface as a producer.

## Closing Thoughts

The Arrow specification is simply put...awesome. While initiatives like the Python DataFrame Protocol have tried to solve the issue of interchange, the usefulness of those initiatives has always been lacking. The Arrow C Data Interface is the tool developers have always needed to make analytics integrations *easy*.

pantab is not the first library to take advantage of these features. The Arrow ADBC drivers I [previously blogged about]({% post_url 2023-06-13-leveraging-the-adbc-driver-in-analytics-workflows %}) are also huge users of nanoarrow / the Arrow C Data Interface, and heavily influenced the design of pantab. Beyond this post you may even more libraries on the [Powered By Apache Arrow](https://arrow.apache.org/powered_by/) project page. Simply put, I am excited to see usage of these great tools grow and make open-source data integrations more powerful than ever before.
