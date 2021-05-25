=======================
Command Line User Guide
=======================

The rasterio command line interface plugins allow you to execute commands that
operate on a raster dataset. Online help lists the avalable subcommands, including those
added by rio-terrain.

.. code-block:: console

	.. click:: rio
	  :prog: rio
	  :nested: none


The list below describes the purpose of the individual rio-terrain subcommands. Command usage can be had by accessing the ``--help`` of each command.

aspect
------

.. code-block:: console

.. click:: aspect:rio
  :prog: aspect
  :nested: none


curvature
---------

.. code-block:: console

	$ rio curvature --help
	Usage: rio curvature [OPTIONS] INPUT OUTPUT

	  Calculate curvature of a raster.

	  INPUT should be a single-band raster.

	  Example:
	  rio curvature elevation.tif curvature.tif

	Options:
	  --neighbors [4|8]     Specifies the number of neighboring cells to use.
	  --stats / --no-stats  Print basic curvature statistics.
	  -j, --njobs INTEGER   Number of concurrent jobs to run
	  -v, --verbose         Enables verbose mode.
	  --version             Show the version and exit.
	  --help                Show this message and exit.

difference
----------

.. code-block:: console

	$ rio difference --help
	Usage: rio difference [OPTIONS] INPUT_T0 INPUT_T1 OUTPUT

	  Subtract INPUT_T0 from INPUT_T1.

	  INPUT_T0 should be a single-band raster at time t0.
	  INPUT_T1 should be a single-band raster at time t1.

	  Example:
	  rio diff elevation1.tif elevation2.tif, diff2_1.tif

	Options:
	  -b, --blocks INTEGER  Multiply TIFF block size by an amount to make chunks
	  -j, --njobs INTEGER   Number of concurrent jobs to run.
	  -v, --verbose         Enables verbose mode.
	  --version             Show the version and exit.
	  --help                Show this message and exit.

extract
-------

.. code-block:: console

	$ rio extract --help
	Usage: rio extract [OPTIONS] INPUT CATEGORICAL OUTPUT

	  Extract regions from a raster by category.

	  INPUT should be a single-band raster.
	  CATEGORICAL should be a single-band raster with categories to extract.

	  The categorical data may be the input raster or another raster.

	  Example:
	  rio extract diff.tif categorical.tif extract.tif -c 1 -c 3

	Options:
	  -c, --category INTEGER  Category to extract.
	  -j, --njobs INTEGER     Number of concurrent jobs to run
	  -v, --verbose           Enables verbose mode.
	  --version               Show the version and exit.
	  --help                  Show this message and exit.

label
-----

.. code-block:: console

	$ rio label --help
	Usage: rio label [OPTIONS] INPUT OUTPUT

	  Label regions in a raster.

	  INPUT should be a single-band raster.

	  Example:
	  rio label blobs.tif labeled_blobs.tif

	Options:
	  --diagonals / --no-diagonals  Label diagonals as connected
	  --zeros / --no-zeros          Use the raster nodata value or zeros for False
	                                condition
	  -j, --njobs INTEGER           Number of concurrent jobs to run
	  -v, --verbose                 Enables verbose mode.
	  --version                     Show the version and exit.
	  --help                        Show this message and exit.

mad
---

.. code-block:: console

	$ rio mad --help
	Usage: rio mad [OPTIONS] INPUT OUTPUT

	  Calculate a median absolute deviation raster.

	  INPUT should be a single-band raster.

	  Example:
	  rio mad elevation.tif mad.tif

	Options:
	  -n, --neighborhood INTEGER  Neighborhood size in cells.
	  -b, --blocks INTEGER        Multiply TIFF block size by an amount to make
	                              chunks
	  -j, --njobs INTEGER         Number of concurrent jobs to run.
	  -v, --verbose               Enables verbose mode.
	  --version                   Show the version and exit.
	  --help                      Show this message and exit.

quantiles
---------

.. code-block:: console

	$ rio quantiles --help
	Usage: rio quantiles [OPTIONS] INPUT

	  Calculate and print quantile values.

	  INPUT should be a single-band raster.

	  Example:
	  rio quantiles elevation.tif -q 0.5 -q 0.9

	Options:
	  -q, --quantile FLOAT        Print quantile value
	  -f, --fraction FLOAT        Randomly sample a fraction of data blocks
	  --absolute / --no-absolute  Calculate quantiles based on the set of absolute
	                              values
	  --describe / --no-describe  Print descriptive statistics to the console
	  --plot / --no-plot          Display statistics plots
	  -j, --jobs INTEGER          Number of concurrent jobs to run
	  -v, --verbose               Enables verbose mode
	  --version                   Show the version and exit.
	  --help                      Show this message and exit.

slice
-----

.. code-block:: console

	$ rio slice --help
	Usage: rio slice [OPTIONS] INPUT OUTPUT

	  Extract regions from a raster by a data range.

	  INPUT should be a single-band raster.

	  Setting the --keep-data option will return the data values.
	  The default is to return a raster of ones and zeros.

	  Example:
	  rio range diff.tif extracted.tif --minumum -2.0 --maximum 2.0

	Options:
	  --minimum FLOAT               Minimum value to extract.
	  --maximum FLOAT               Maximum value to extract.
	  --keep-data / --no-keep-data  Return the input data. Default is to return
	                                ones.
	  --zeros / --no-zeros          Use the raster nodata value or zeros for False
	                                condition
	  -j, --njobs INTEGER           Number of concurrent jobs to run
	  -v, --verbose                 Enables verbose mode.
	  --version                     Show the version and exit.
	  --help                        Show this message and exit.

slope
-----

.. code-block:: console

	$ rio slope --help
	Usage: rio slope [OPTIONS] INPUT OUTPUT

	  Calculate slope of a raster.

	  INPUT should be a single-band raster.

	  Example:
	  rio slope elevation.tif slope.tif

	Options:
	  --neighbors [4|8]            Specifies the number of neighboring cells to
	                               use.
	  -u, --units [grade|degrees]  Specifies the units of slope.
	  -b, --blocks INTEGER         Multiply TIFF block size by an amount to make
	                               chunks
	  -j, --njobs INTEGER          Number of concurrent jobs to run.
	  -v, --verbose                Enables verbose mode.
	  --version                    Show the version and exit.
	  --help                       Show this message and exit.

std
---

.. code-block:: console

	$ rio std --help
	Usage: rio std [OPTIONS] INPUT OUTPUT

	  Calculate a standard-deviation raster.

	  INPUT should be a single-band raster.

	  Example:
	  rio std elevation.tif stddev.tif

	Options:
	  -n, --neighborhood INTEGER  Neigborhood size in cells.
	  -b, --blocks INTEGER        Multiply TIFF block size by an amount to make
	                              chunks
	  -j, --njobs INTEGER         Number of concurrent jobs to run
	  -v, --verbose               Enables verbose mode.
	  --version                   Show the version and exit.
	  --help                      Show this message and exit.

threshold
---------

.. code-block:: console

	$ rio threshold --help
	Usage: rio threshold [OPTIONS] INPUT UNCERTAINTY OUTPUT LEVEL

	  Threshold a raster with an uncertainty raster.

	  INPUT should be a single-band raster.
	  UNCERTAINTY should be a single-band raster representing uncertainty.

	  Example:
	  rio threshold diff.tif uncertainty.tif, detected.tif 1.68

	Options:
	  -j, --njobs INTEGER  Number of concurrent jobs to run.
	  -v, --verbose        Enables verbose mode.
	  --version            Show the version and exit.
	  --help               Show this message and exit.

uncertainty
-----------

.. code-block:: console

	$ rio uncertainty --help
	Usage: rio uncertainty [OPTIONS] UNCERTAINTY0 UNCERTAINTY1 OUTPUT

	  Calculate a level-of-detection raster.

	  UNCERTAINTY0 should be a single-band raster representing level of uncertainty at time 0.
	  UNCERTAINTY1 should be a single-band raster representing level of uncertainty at time 1.

	  Example:
	  rio uncertainty roughness_t0.tif roughness_t1.tif uncertainty.tif

	Options:
	  --instrumental0 FLOAT  Instrumental or minimum uncertainty for the first
	                         raster.
	  --instrumental1 FLOAT  Instrumental or minimum uncertainty for the second
	                         raster.
	  -j, --njobs INTEGER    Number of concurrent jobs to run.
	  -v, --verbose          Enables verbose mode.
	  --version              Show the version and exit.
	  --help                 Show this message and exit.
