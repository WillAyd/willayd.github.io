---
title: "Leveraging the ADBC driver in Analytics Workflows"
date: 2023-06-16T00:00:00
description: This blog post describes the actively developed ADBC driver and what it means for libraries like pandas.
categories:
  - performance
tags:
  - python
  - adbc
# cSpell:ignore ADBC JDBC ODBC adbc numpy pyarrow sqlalchemy dbapi functools kwargs randint dtypes dtype pyarrow astype
---

The [ADBC: Arrow Database Connectivity](https://arrow.apache.org/docs/format/ADBC.html) client API standard is new standard [introduced in January 2023](https://arrow.apache.org/blog/2023/01/05/introducing-arrow-adbc/). Sparing some technical details, traditional formats like ODBC/JDBC has operated on data in a *row-oriented* manner. This made sense at the time those standards were created (in the 1990s) as the databases they targeted were pre-dominantly row-oriented as well. The past decade of analytics has shown a strong inclination towards *column-oriented* database storage, so using ODBC/JDBC to transfer data means you at a minimum always have to spend resources to translate to/from row- and column-oriented formats.

Many column databases solve the row->column transposition issue by ingesting or exporting columnar file formats like [Apache Parquet](https://parquet.apache.org/docs/file-format/). This can be an indispensable tool for achieving high throughput, but in going this route you often sacrifice the ecosystem benefits of standard tooling like ODBC/JDBC. Using pandas as an example, I can very easily read/write from almost any database using [pd.read_sql](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_sql.html) and [pd.DataFrame.to_sql](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_sql.html). This works well for smallish datasets, but when you run into scalability issues you often end up exporting/importing via CSV/parquet, adding more potential points of breakage to your pipelines.

Its worth nothing that even if your source/target database is not columnar, ADBC has an advantage of being implemented at a low level. ADBC is tightly integrated with the [Arrow Columnar Format](https://arrow.apache.org/docs/format/Columnar.html), which essentially means that ADBC can optimally work with the data using its primitive layout in memory. Pandas by contrast does NOT have this, so all of the ``to_sql`` and ``read_sql`` calls you make in pandas have to do a lot of extra work at runtime to have database communications fit into the pandas data model. This is by no means free and one of the reasons why SQL interaction in pandas is slow, not to mention all the extra hoops pandas has to jump through to (oftentimes unsuccessfully) manage data types.

To see how much ADBC could help my workflows I decided to test things out against the Python ADBC Postgres Driver and compare it to the functional equivalent in pandas. As of writing the ADBC Postgres driver is still [considered experimental](https://arrow.apache.org/adbc/main/driver/status.html), but I encourage you to [install it on your own](https://arrow.apache.org/adbc/main/driver/installation.html) and try it out!

## Performance Benchmarking

The following code serves as a crude benchmark for performance. If you'd like to run this on your end, simply tweak ``PG_URI`` to match your database configuration.

```python
import functools
import time
from collections.abc import Callable

import numpy as np
import pandas as pd
import pyarrow as pa
import sqlalchemy as sa
from adbc_driver_postgresql import dbapi


PG_URI = "postgresql://"


def print_runtime(func: Callable):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        runtime = end - start
        print(f"function {func.__name__} took {runtime}")

        return result

    return wrapper


@print_runtime
def write_pandas(df: pd.DataFrame):
    table_name = "pandas_data"
    engine = sa.create_engine(PG_URI)
    df.to_sql(table_name, engine, if_exists="replace", method="multi", index=False)


@print_runtime
def write_arrow(tbl: pa.Table):
    table_name = "arrow_data"
    with dbapi.connect(PG_URI) as conn:
        with conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {table_name}")

        with conn.cursor() as cur:
            cur.adbc_ingest(table_name, tbl)

        conn.commit()

@print_runtime
def read_pandas() -> pd.DataFrame:
    table_name = "pandas_data"
    engine = sa.create_engine(PG_URI)
    return pd.read_sql(f"SELECT * FROM {table_name}", engine)


@print_runtime
def read_arrow() -> pa.Table:
    table_name = "arrow_data"
    with dbapi.connect(PG_URI) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT * FROM {table_name}")
            return cur.fetch_arrow_table()


if __name__ == "__main__":
    np.random.seed(42)
    df = pd.DataFrame(np.random.randint(10_000, size=(100_000, 10)), columns=list("abcdefghij"))
    tbl = pa.Table.from_pandas(df)

    write_pandas(df)
    write_arrow(tbl)

    df_new = read_pandas()
    tbl_new = read_arrow()
```

Executing this very unscientific benchmark yields the following results on my machine:

```sh
function write_pandas took 11.065816879272461
function write_arrow took 1.1672894954681396
function read_pandas took 0.2586965560913086
function read_arrow took 0.0703287124633789
```

From this we can see the ADBC connector is significantly faster on both read and write. Keep in mind that Postgres is a *row-oriented* database; my expectation is that the performance benefits would be even bigger for a *column-oriented* database!

## Better Data Types

If you've worked with pandas in an ETL workflow, chances are high that you've had to do some post-processing on numeric data. This happens often with nullable integral data (which the NumPy backend to pandas physically cannot store), but can also happen for many other reasons that differ across databases / driver implementations. For the sake of illustration, let's append a row of NULL values to our tables.

```sql
INSERT INTO arrow_data VALUES (NULL);
INSERT INTO pandas_data VALUES (NULL);
```

This has no impact on the arrow code we wrote previously

```python
>>> tbl_new = read_arrow()
>>> tbl.schema == tbl_new.schema
True
```

But will impact the pandas code

```python
>>> df_new = read_pandas()
>>> (df.dtypes == df_new.dtypes).all()
False
```

Even though nothing changed with the data type in the database, we've gone from using integral data in pandas / postgres to now introducing float data in pandas, solely due to the introduction of ``NULL`` values in postgres. This can come up unexpectedly and be very surprising. To prevent this on the pandas side, you will see things like:

```python
>>> df_new = df_new.astype("Int32")
```

OR

```python
>>> table_name = "pandas_data"
>>> engine = sa.create_engine(PG_URI)
>>> df_new = pd.read_sql_query(f"SELECT * FROM {table_name}", engine, dtype="Int32")
```

OR (starting in pandas 2.0)

```python
>>> table_name = "pandas_data"
>>> engine = sa.create_engine(PG_URI)
>>> df_new = pd.read_sql(f"SELECT * FROM {table_name}", engine,
...   dtype_backend="pyarrow")
```

These are 3 different ways to solve the problem, each introducing their own subsequent nuance. If you already knew about the issues with nullable integral data and the NumPy backend in pandas then maybe this isn't surprising, but not every user has or needs to have that low-level of an understanding of pandas. This was also a controlled example; in the real world you either need to be overly defensive or open to surprise when minor changes in your database data change your pandas data types and subsequent workflows. With the ADBC driver you do not have this issue; the data type you read is simply inferred from the database metadata.

## Closing Thoughts

I for one am really excited to see how ADBC continues to evolve. Moving data from one database to another takes up a significant amount of my time as a data engineer, and the ability to do that faster with cleaner data types will be powerful. As more databases (particularly columnar ones) implement [Arrow Flight SQL](https://arrow.apache.org/docs/format/FlightSql.html) or at least provide ADBC clients I expect a lot of ETL tools to start leveraging ADBC drivers in turn.
