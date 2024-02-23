---
title: "Leveraging the Arrow C Data Interface"
date: 2024-02-20T00:00:00
description: This blog post describes how the Arrow C Data interface works, as witnessed through transformation of the pantab library.
categories:
  - arrow
tags:
  - python
  - arrow
# cSpell:ignore pantab BITMASK BYTEMASK nanoarrow pyarrow pydict adbc ADBC Joris Bossche bitmasks itertuples fillcolor rawdata forloop
---

The [Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html) is an amazing tool, and while it documents its own potential use cases I wanted to dedicate a blog post to my personal experience using it.

## Problem Statement

Transferring data across systems and libraries is difficult and time-consuming. This statement applies not only to compute time but perhaps more importantly to developer time as well.

I first ran into this issue over 5 years ago when I started a library called [pantab](https://pantab.readthedocs.io/en/latest/). At the time, I had just become a core developer of [pandas](https://pandas.pydata.org/), and through consulting work had been dealing a lot with [Tableau](https://www.tableau.com/). Tableau had just released their [Hyper API](https://www.tableau.com/developer/learning/tableau-hyper-api), which is a way to exchange data to/from their proprietary Hyper database.

*Great...*, I said to myself, *I know a lot of pandas internals and I think writing a DataFrame to a Hyper database will be easier than any other option*. Hence, pantab was created.

As you may or may not already be aware, most high-performance Python libraries in the analytics space get their performance from implementing parts of their code base in *lower-level* languages like C/C++/Rust. So with pantab I set out to do the same thing.

The problem, however, is that pandas did NOT expose any of its internal data structures to other libraries. pantab was forced to hack a lot of things to make this integration "work", but in a way that was very fragile across pandas releases.

Late in 2023 I decided that pantab was due for a rewrite. Hacking into the pandas internals was not going to work any more, especially as the number of data types that pandas supported started to grow. What pantab needed was an agreement with a library like pandas as to how to exchange low-level data at an extremely high level of performance.

Fortunately, I wasn't the only person with that idea. Data interchange libraries that weren't even a thought when pantab started were now a reality, so it was time to test those out.

## Status Quo

pantab initially used [pandas.DataFrame.itertuples](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.itertuples.html) to loop over every row and every element within a DataFrame before writing it out to a Hyper file. While this worked and was faster than what most users would write by hand, it still really wasn't that fast.

Here is a high level overview of that process, with heavy Python runtime interactions highlighted in red:

<!--
digraph G {
  node [
    shape=box
    style=filled
    color=black
    fillcolor=white
  ]

  rawdata [
    label = "df.itertuples()"
    color="#b20100"
    fillcolor="#edd5d5"
  ]
  df -> rawdata;

  forloop [
    label = "Python for loop"
    color="#b20100"
    fillcolor="#edd5d5"
  ]
  rawdata -> forloop;

  convert [
    label = "PyObject -> primitive"
    color="#b20100"
    fillcolor="#edd5d5"
  ]
  forloop -> convert;

  write [
    label = "Database write"
  ]
  convert -> write;
}
}-->

<svg width="180pt" height="332pt"
 viewBox="0.00 0.00 180.00 332.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 328)">
<title>G</title>
<polygon fill="white" stroke="transparent" points="-4,4 -4,-328 176,-328 176,4 -4,4"/>
<!-- rawdata -->
<g id="node1" class="node">
<title>rawdata</title>
<polygon fill="#edd5d5" stroke="#b20100" points="143.5,-252 28.5,-252 28.5,-216 143.5,-216 143.5,-252"/>
<text text-anchor="middle" x="86" y="-230.3" font-family="Times,serif" font-size="14.00">df.itertuples()</text>
</g>
<!-- forloop -->
<g id="node3" class="node">
<title>forloop</title>
<polygon fill="#edd5d5" stroke="#b20100" points="149,-180 23,-180 23,-144 149,-144 149,-180"/>
<text text-anchor="middle" x="86" y="-158.3" font-family="Times,serif" font-size="14.00">Python for loop</text>
</g>
<!-- rawdata&#45;&gt;forloop -->
<g id="edge2" class="edge">
<title>rawdata&#45;&gt;forloop</title>
<path fill="none" stroke="black" d="M86,-215.7C86,-207.98 86,-198.71 86,-190.11"/>
<polygon fill="black" stroke="black" points="89.5,-190.1 86,-180.1 82.5,-190.1 89.5,-190.1"/>
</g>
<!-- df -->
<g id="node2" class="node">
<title>df</title>
<polygon fill="white" stroke="black" points="113,-324 59,-324 59,-288 113,-288 113,-324"/>
<text text-anchor="middle" x="86" y="-302.3" font-family="Times,serif" font-size="14.00">df</text>
</g>
<!-- df&#45;&gt;rawdata -->
<g id="edge1" class="edge">
<title>df&#45;&gt;rawdata</title>
<path fill="none" stroke="black" d="M86,-287.7C86,-279.98 86,-270.71 86,-262.11"/>
<polygon fill="black" stroke="black" points="89.5,-262.1 86,-252.1 82.5,-262.1 89.5,-262.1"/>
</g>
<!-- convert -->
<g id="node4" class="node">
<title>convert</title>
<polygon fill="#edd5d5" stroke="#b20100" points="172,-108 0,-108 0,-72 172,-72 172,-108"/>
<text text-anchor="middle" x="86" y="-86.3" font-family="Times,serif" font-size="14.00">PyObject &#45;&gt; primitive</text>
</g>
<!-- forloop&#45;&gt;convert -->
<g id="edge3" class="edge">
<title>forloop&#45;&gt;convert</title>
<path fill="none" stroke="black" d="M86,-143.7C86,-135.98 86,-126.71 86,-118.11"/>
<polygon fill="black" stroke="black" points="89.5,-118.1 86,-108.1 82.5,-118.1 89.5,-118.1"/>
</g>
<!-- write -->
<g id="node5" class="node">
<title>write</title>
<polygon fill="white" stroke="black" points="148.5,-36 23.5,-36 23.5,0 148.5,0 148.5,-36"/>
<text text-anchor="middle" x="86" y="-14.3" font-family="Times,serif" font-size="14.00">Database write</text>
</g>
<!-- convert&#45;&gt;write -->
<g id="edge4" class="edge">
<title>convert&#45;&gt;write</title>
<path fill="none" stroke="black" d="M86,-71.7C86,-63.98 86,-54.71 86,-46.11"/>
<polygon fill="black" stroke="black" points="89.5,-46.1 86,-36.1 82.5,-46.1 89.5,-46.1"/>
</g>
</g>
</svg>

A later version of pantab which required a minimum of pandas 1.3 ended up hacking into the internals of pandas, calling something like ``df._mgr.column_arrays`` to get a ``NumPy`` array for each column in the DataFrame. Combined with the [NumPy Array Iterator API](https://numpy.org/doc/stable/reference/c-api/iterator.html), pantab could iterate over raw NumPy arrays instead of doing a loop in Python.

<!--
digraph G {
  node [
    shape=box
    style=filled
    color=black
    fillcolor=white
  ]

  rawdata [
    label = "df._mgr.column_arrays"
    color="#b20100"
    fillcolor="#edd5d5"
  ]
  df -> rawdata;

  forloop [
    label = "NumPy Array Iterator API"
  ]
  rawdata -> forloop;

  string [
    label = "Is string?"
    shape = diamond
    color=black
    fillcolor=white
  ]

  forloop -> string;

  convert [
    label = "PyObject -> primitive"
    color="#b20100"
    fillcolor="#edd5d5"
  ]
  string -> convert [
    label="yes"
  ]

  write [
    label = "Database write"
  ]
  string -> write [
    label="no"
  ]
  convert -> write;
}
-->

<svg width="257pt" height="423pt"
 viewBox="0.00 0.00 256.50 423.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 419)">
<title>G</title>
<polygon fill="white" stroke="transparent" points="-4,4 -4,-419 252.5,-419 252.5,4 -4,4"/>
<!-- rawdata -->
<g id="node1" class="node">
<title>rawdata</title>
<polygon fill="#edd5d5" stroke="#b20100" points="236,-342 58,-342 58,-306 236,-306 236,-342"/>
<text text-anchor="middle" x="147" y="-320.3" font-family="Times,serif" font-size="14.00">df._mgr.column_arrays</text>
</g>
<!-- forloop -->
<g id="node3" class="node">
<title>forloop</title>
<polygon fill="white" stroke="black" points="248.5,-269 45.5,-269 45.5,-233 248.5,-233 248.5,-269"/>
<text text-anchor="middle" x="147" y="-247.3" font-family="Times,serif" font-size="14.00">NumPy Array Iterator API</text>
</g>
<!-- rawdata&#45;&gt;forloop -->
<g id="edge2" class="edge">
<title>rawdata&#45;&gt;forloop</title>
<path fill="none" stroke="black" d="M147,-305.81C147,-297.79 147,-288.05 147,-279.07"/>
<polygon fill="black" stroke="black" points="150.5,-279.03 147,-269.03 143.5,-279.03 150.5,-279.03"/>
</g>
<!-- df -->
<g id="node2" class="node">
<title>df</title>
<polygon fill="white" stroke="black" points="174,-415 120,-415 120,-379 174,-379 174,-415"/>
<text text-anchor="middle" x="147" y="-393.3" font-family="Times,serif" font-size="14.00">df</text>
</g>
<!-- df&#45;&gt;rawdata -->
<g id="edge1" class="edge">
<title>df&#45;&gt;rawdata</title>
<path fill="none" stroke="black" d="M147,-378.81C147,-370.79 147,-361.05 147,-352.07"/>
<polygon fill="black" stroke="black" points="150.5,-352.03 147,-342.03 143.5,-352.03 150.5,-352.03"/>
</g>
<!-- string -->
<g id="node4" class="node">
<title>string</title>
<polygon fill="white" stroke="black" points="147,-196 69.58,-178 147,-160 224.42,-178 147,-196"/>
<text text-anchor="middle" x="147" y="-174.3" font-family="Times,serif" font-size="14.00">Is string?</text>
</g>
<!-- forloop&#45;&gt;string -->
<g id="edge3" class="edge">
<title>forloop&#45;&gt;string</title>
<path fill="none" stroke="black" d="M147,-232.81C147,-224.79 147,-215.05 147,-206.07"/>
<polygon fill="black" stroke="black" points="150.5,-206.03 147,-196.03 143.5,-206.03 150.5,-206.03"/>
</g>
<!-- convert -->
<g id="node5" class="node">
<title>convert</title>
<polygon fill="#edd5d5" stroke="#b20100" points="172,-109 0,-109 0,-73 172,-73 172,-109"/>
<text text-anchor="middle" x="86" y="-87.3" font-family="Times,serif" font-size="14.00">PyObject &#45;&gt; primitive</text>
</g>
<!-- string&#45;&gt;convert -->
<g id="edge4" class="edge">
<title>string&#45;&gt;convert</title>
<path fill="none" stroke="black" d="M136.37,-162.19C127.53,-149.87 114.73,-132.04 104.25,-117.43"/>
<polygon fill="black" stroke="black" points="107.07,-115.36 98.39,-109.27 101.38,-119.44 107.07,-115.36"/>
<text text-anchor="middle" x="133.5" y="-130.8" font-family="Times,serif" font-size="14.00">yes</text>
</g>
<!-- write -->
<g id="node6" class="node">
<title>write</title>
<polygon fill="white" stroke="black" points="209.5,-36 84.5,-36 84.5,0 209.5,0 209.5,-36"/>
<text text-anchor="middle" x="147" y="-14.3" font-family="Times,serif" font-size="14.00">Database write</text>
</g>
<!-- string&#45;&gt;write -->
<g id="edge5" class="edge">
<title>string&#45;&gt;write</title>
<path fill="none" stroke="black" d="M157.6,-162.29C170.72,-142.23 190.27,-105.12 181,-73 178.13,-63.05 172.82,-53.16 167.23,-44.62"/>
<polygon fill="black" stroke="black" points="169.99,-42.46 161.4,-36.26 164.25,-46.46 169.99,-42.46"/>
<text text-anchor="middle" x="192" y="-87.3" font-family="Times,serif" font-size="14.00">no</text>
</g>
<!-- convert&#45;&gt;write -->
<g id="edge6" class="edge">
<title>convert&#45;&gt;write</title>
<path fill="none" stroke="black" d="M100.77,-72.81C108.26,-64.09 117.5,-53.34 125.74,-43.75"/>
<polygon fill="black" stroke="black" points="128.51,-45.89 132.37,-36.03 123.2,-41.33 128.51,-45.89"/>
</g>
</g>
</svg>

This helped a lot with performance, and while the NumPy Array Iterator API was solid, the pandas internals [would change across releases](https://github.com/innobi/pantab/issues/190), so it took a lot of developer time to maintain.

The images and comments above assume we are writing a DataFrame to a Hyper file. Going the other way around, pantab would create a Python list of PyObjects and convert to more appropriate data types after everything was read. If we were to graph that process, it would be even more red - not good!

## Initial Redesign Attempt - Python DataFrame Interchange Protocol

Before I ever considered the Arrow C Data Interface, my first try at getting high performance and easy data exchange from pandas to Hyper was through the [Python DataFrame interchange protocol](https://data-apis.org/dataframe-protocol/latest/purpose_and_scope.html). While initially promising, this soon became problematic.

For starters, *Memory ownership and lifetime* is listed as something in scope of the protocol, but is not actually defined. Implementers are free to choose how long a particular buffer should last, and it is up the client to just know this. After many unexpected segfaults, I started to grow weary of this solution.

Another major issue for the interchange protocol is that *Non-Python API standardization (e.g., C/C++ APIs)* is explicitly a non-goal. With pantab being a consumer of raw data, this meant I had to know how to manage those raw buffers for every type I wished to consume.  While that may not be a huge deal for simple primitive types like sized integers, it leaves much to be desired when you try to work with more complex types like decimals.

Next topic - nullability! Here is the enumeration the protocol specified:

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

The way the DataFrame Interchange Protocol decided to handle nullability is an area where trying to be inclusive of many different strategies ended up as a detriment to all. Requiring developers to integrate all of these methods across any type they may consume is a lot of effort (particularly for ``USE_SENTINEL``).

Another limitation with the DataFrame Interchange Protocol is the fact that it only talks about how to consume data, but offers no guidance on how to produce it. If starting from your extension, you have no tools or library to manually build buffers. Much like the [status quo](#status-quo), this meant reading from a Hyper database to a pandas DataFrame would likely be going through Python objects.

Finally, and related to all of the issues above, the pandas implementation of the DataFrame Interchange Protocol left a lot to be desired. While started with good intentions, it never got the attention needed to make it really effective. I already mentioned the lifetime issues across various data types, but nullability handling was all over the place across types. Metadata was often passed along incorrectly from pandas down through the interface...essentially making it a very high effort for consumers to try and use it.

## Arrow C Data Interface to the Rescue

After stumbling around the DataFrame Protocol Interface for a few weeks, [Joris Van den Bossche](https://jorisvandenbossche.github.io/pages/about.html) asked me why I didn't look at the [Arrow C Data Interface](https://arrow.apache.org/docs/format/CDataInterface.html). The answer of course was that I was just not very familiar with it. Joris knows a ton about pandas and Arrow, so I figured it best to take his word for it and try it out.

Almost immediately my issues went away. To wit:

  1. Memory ownership and lifetime - [well defined](https://arrow.apache.org/docs/format/CDataInterface.html#memory-management) at low levels
  2. Non-Python API - for this there is [nanoarrow](https://arrow.apache.org/nanoarrow/latest/index.html)
  3. Nullability handling - uses Arrow bitmasks
  4. Producing buffers - can create (not just read) data
  5. pandas implementation - it *just works* via [PyCapsules](https://arrow.apache.org/docs/format/CDataInterface/PyCapsuleInterface.html#arrowstream-export)

With well defined memory semantics, a low-level API and clean nullability handling, the amount of extension code I had to write was drastically reduced. I felt more confident in the implementation and had to deal with less memory corruption / crashes than before. And, perhaps most importantly, I saved a lot of time.

See the image below for a high level overview of the process. Note the lack of any red compared to the [status quo](#status-quo) - this has a very limited interaction with the Python runtime:

<!--
digraph G {
  node [
    shape=box
    style=filled
    color=black
    fillcolor=white
  ]

  rawdata [
    label = "df.__arrow_c_stream__()"
  ]
  df -> rawdata;

  forloop [
    label = "Arrow C API / nanoarrow"
  ]
  rawdata -> forloop;

  write [
    label = "Database write"
  ]
  forloop -> write
}
-->

<svg width="202pt" height="260pt"
 viewBox="0.00 0.00 202.00 260.00" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<g id="graph0" class="graph" transform="scale(1 1) rotate(0) translate(4 256)">
<title>G</title>
<polygon fill="white" stroke="transparent" points="-4,4 -4,-256 198,-256 198,4 -4,4"/>
<!-- rawdata -->
<g id="node1" class="node">
<title>rawdata</title>
<polygon fill="white" stroke="black" points="189.5,-180 4.5,-180 4.5,-144 189.5,-144 189.5,-180"/>
<text text-anchor="middle" x="97" y="-158.3" font-family="Times,serif" font-size="14.00">df.__arrow_c_stream__()</text>
</g>
<!-- forloop -->
<g id="node3" class="node">
<title>forloop</title>
<polygon fill="white" stroke="black" points="194,-108 0,-108 0,-72 194,-72 194,-108"/>
<text text-anchor="middle" x="97" y="-86.3" font-family="Times,serif" font-size="14.00">Arrow C API / nanoarrow</text>
</g>
<!-- rawdata&#45;&gt;forloop -->
<g id="edge2" class="edge">
<title>rawdata&#45;&gt;forloop</title>
<path fill="none" stroke="black" d="M97,-143.7C97,-135.98 97,-126.71 97,-118.11"/>
<polygon fill="black" stroke="black" points="100.5,-118.1 97,-108.1 93.5,-118.1 100.5,-118.1"/>
</g>
<!-- df -->
<g id="node2" class="node">
<title>df</title>
<polygon fill="white" stroke="black" points="124,-252 70,-252 70,-216 124,-216 124,-252"/>
<text text-anchor="middle" x="97" y="-230.3" font-family="Times,serif" font-size="14.00">df</text>
</g>
<!-- df&#45;&gt;rawdata -->
<g id="edge1" class="edge">
<title>df&#45;&gt;rawdata</title>
<path fill="none" stroke="black" d="M97,-215.7C97,-207.98 97,-198.71 97,-190.11"/>
<polygon fill="black" stroke="black" points="100.5,-190.1 97,-180.1 93.5,-190.1 100.5,-190.1"/>
</g>
<!-- write -->
<g id="node4" class="node">
<title>write</title>
<polygon fill="white" stroke="black" points="159.5,-36 34.5,-36 34.5,0 159.5,0 159.5,-36"/>
<text text-anchor="middle" x="97" y="-14.3" font-family="Times,serif" font-size="14.00">Database write</text>
</g>
<!-- forloop&#45;&gt;write -->
<g id="edge3" class="edge">
<title>forloop&#45;&gt;write</title>
<path fill="none" stroke="black" d="M97,-71.7C97,-63.98 97,-54.71 97,-46.11"/>
<polygon fill="black" stroke="black" points="100.5,-46.1 97,-36.1 93.5,-46.1 100.5,-46.1"/>
</g>
</g>
</svg>

Without going too deep in the benchmarks game, the Arrow C Data Interface implementation yielded a 25% performance improvement for me when writing strings. When reading data, it was more like a 500% improvement than what had been previously implemented. Not bad...

My code is no longer tied to the potentially fragile internals of pandas, and with the stability of the Arrow C Data Interface things are far less likely to break when new versions are released.

## Bonus Feature - Bring Your Own Library

While it wasn't my goal at the outset, implementing the Arrow C Data Interface had the benefit of decoupling a dependency on pandas. pandas was the de facto library when pantab was first written, but since then many high quality Arrow-based libraries have popped up.

With the Arrow C Data Interface, pantab now has a *bring your own DataFrame library mentality*.

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

These all produce the same results, and as the author of pantab I did not have to do anything extra to accommodate the various libraries - everything *just works*.

## Closing Thoughts

The Arrow specification is simply put...awesome. While initiatives like the Python DataFrame Protocol have tried to solve the issue of interchange, I don't believe that goal was ever achieved...until now. The Arrow C Data Interface is the tool developers have always needed to make analytics integrations *easy*.

pantab is not the first library to take advantage of these features. The Arrow ADBC drivers I [previously blogged about]({% post_url 2023-06-13-leveraging-the-adbc-driver-in-analytics-workflows %}) are also huge users of nanoarrow / the Arrow C Data Interface, and heavily influenced the design of pantab. The [Powered By Apache Arrow](https://arrow.apache.org/powered_by/) project page is the best resource to find others as they get developed in the future.

I, for one, am excited to see Arrow-based tooling grow and make open-source data integrations more powerful than ever before.
