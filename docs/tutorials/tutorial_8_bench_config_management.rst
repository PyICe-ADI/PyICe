========================
TUTORIAL 8 Bench Configuration Management
========================

Storing data in a SQLite database can be intimidating for first time users. It's always tempting to go to what we know such as CSV, etc.
This is also true of Python in general.
The reader is encouraged to give both a try and embrace the possibility, although there will be growing pains, that the advancement in productivity and organization will follow from this investment.

One way to learn about the database and practice using SQL queries is in the DB Browser. The browser has simple tabs across the top called:

**[Database Structure]** **[Browse Data]** **[Edit Pragmas]** **[Execute SQL]**

We will focus on the first, second and fourth.

In **Database Structure** notice that our two tables are listed, *diode_data_table* and *tutorial_2_table*.
These can be unfolder to show the columns (PyICe channels) in each table.

By going to the **Browse Data** tab we can choose which of the two tables to view from the dropdown in the upper left.
Notice that it now gives a complete world view of the columns and rows of data taken. There is a column for each PyICe channel and row for each call of the logger (logger.log()) that was in the **for** loop.

Finally, if we go to the **Execute SQL** tab we can try our hand at some SQL queries. This tab is not table specific as SQL queries generally need to be disambiguated from within the query itself.

For example, we can borrow a query from Tutorial 6 and simply paste it in the query input box.

.. code-block:: text

   SELECT rowid, vmeas*1e6 FROM tutorial_2_table ORDER BY rowid

Now by hitting the *play* button [▶] we can see the data listed in the browser pane below and the status of the query result in the lowest browser pane.

DB Broswer can also make quick and dirty charts in the lower right pane to sanity check the results before committing to an LTC_plot script. This can also be helpful to find the extents of the data.

Another way to interrogate data values and determine Python data types while learning these techniques is to simply stop the program midstream and poke around.
To that end, the Python command **breakpoint()** can be very powerful. From within a breakpoint, the programmer can interact with object data simply by typing its name at the **(pdb)** prompt.

For example, it's possible to interrogate the SQLite database values with the following code:

.. code-block:: python

   from PyICe.lab_utils.sqlite_data import sqlite_data
   database = sqlite_data(table_name="diode_data_table", database_file="data_log.sqlite")
   breakpoint()

This will result in the Python command line prompt:
   
.. code-block:: text

   --Return--
   > d:\users\smartin2\projects\pyice-adi\pyice\tutorials\getting_started_tutorials\results\ex_7_tips_and_tricks.py(5)<module>()->None
   -> breakpoint()
   (Pdb) _
   
From this prompt we can examine any local variables in real time with Python functions like **type()**.

.. code-block:: text

   --Return--
   > d:\users\smartin2\projects\pyice-adi\pyice\tutorials\getting_started_tutorials\results\ex_7_tips_and_tricks.py(5)<module>()->None
   -> breakpoint()
   (Pdb) type(database)
   <class 'PyICe.lab_utils.sqlite_data.sqlite_data'>
   (Pdb) _
   
We can also ask objects what methods they support by using the **dir()** function.
   
.. code-block:: text
   
   --Return--
   > d:\users\smartin2\projects\pyice-adi\pyice\tutorials\getting_started_tutorials\results\ex_7_tips_and_tricks.py(5)<module>()->None
   -> breakpoint()
   (Pdb) type(database)
   <class 'PyICe.lab_utils.sqlite_data.sqlite_data'>
   (Pdb) dir(database)
   ['__abstractmethods__', '__class__', '__class_getitem__', '__contains__', '__delattr__', '__dict__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__len__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__reversed__', '__setattr__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__weakref__', '_abc_impl', 'column_query', 'conn', 'convert_ndarray', 'convert_timestring', 'convert_vector', 'count', 'csv', 'expand_vector_data', 'filter_change', 'get_column_names', 'get_column_types', 'get_distinct', 'get_table_names', 'index', 'numpy_recarray', 'optimize', 'pandas_dataframe', 'params', 'query', 'set_table', 'sql_query', 'table_name', 'time_delta_query', 'timezone', 'to_list', 'xlsx', 'zip']
   (Pdb) _
   
Finally, we can try our hand at some SQL queries and see if we get back a data structure.

.. code-block:: text
   
   --Return--
   > d:\users\smartin2\projects\pyice-adi\pyice\tutorials\getting_started_tutorials\results\ex_7_tips_and_tricks.py(5)<module>()->None
   -> breakpoint()
   (Pdb) type(database)
   <class 'PyICe.lab_utils.sqlite_data.sqlite_data'>
   (Pdb) dir(database)
   ['__abstractmethods__', '__class__', '__class_getitem__', '__contains__', '__delattr__', '__dict__', '__dir__', '__doc__', '__enter__', '__eq__', '__exit__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__len__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__reversed__', '__setattr__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__weakref__', '_abc_impl', 'column_query', 'conn', 'convert_ndarray', 'convert_timestring', 'convert_vector', 'count', 'csv', 'expand_vector_data', 'filter_change', 'get_column_names', 'get_column_types', 'get_distinct', 'get_table_names', 'index', 'numpy_recarray', 'optimize', 'pandas_dataframe', 'params', 'query', 'set_table', 'sql_query', 'table_name', 'time_delta_query', 'timezone', 'to_list', 'xlsx', 'zip']
   (Pdb) database.query("SELECT rowid, vmeas*1e6 FROM tutorial_2_table ORDER BY rowid")
   <sqlite3.Cursor object at 0x0000017B30D3E340>
   (Pdb)
   
The database object itself now represents the results of the query. While  the object is a **<sqlite3.Cursor>** object, it will respond to list of list-like inquires.
Specifically, the first index will represent the row of the query result and the second index will represent the column.
To determine how many rows were returned the Python function **len()** can be used.

.. code-block:: text
   
   (Pdb) len(database)
   10
   (Pdb)
   
The sixth row, second column would be retrieved by:

.. code-block:: text
   
   (Pdb) database[5][1]
   -0.637
   (Pdb)

Notice that if we try to access a nonexistent column we get an error:

.. code-block:: text

   database[5][2]
   *** IndexError: tuple index out of range
   (Pdb)
   
Hopefully with these tools, and with the abundance of material online, we can inspire enough confidence to get going using Python and SQLite for more advanced and organized laboratory evaluation. **Enjoy!**