=======================
Command Line User Guide
=======================

The rasterio command line interface plugins allow you to execute commands that
operate on a raster dataset. Online help lists the avalable subcommands, including those
added by rio-terrain.

.. code-block:: console

	$ rio --help
	Usage: rio [OPTIONS] COMMAND [ARGS]...

	  Rasterio command line interface.

	Options:
	  -v, --verbose           Increase verbosity.
	  -q, --quiet             Decrease verbosity.
	  --aws-profile TEXT      Select a profile from the AWS credentials file
	  --aws-no-sign-requests  Make requests anonymously
	  --aws-requester-pays    Requester pays data transfer costs
	  --version               Show the version and exit.
	  --gdal-version
	  --help                  Show this message and exit.

	Commands:
	  aspect       Calculates aspect of a height raster.
	  blocks       Write dataset blocks as GeoJSON features.
	  bounds       Write bounding boxes to stdout as GeoJSON.
	  calc         Raster data calculator.
	  clip         Clip a raster to given bounds.
	  ...

The list below describes the purpose of the individual rio-terrain subcommands. Command usage can be had by accessing the ``--help`` of each command.

aspect
------

.. include:: cli/cli.aspect.txt
   :literal:

curvature
---------

.. include:: cli/cli.curvature.txt
   :literal:

difference
----------

.. include:: cli/cli.difference.txt
   :literal:

extract
-------

.. include:: cli/cli.extract.txt
   :literal:

label
-----

.. include:: cli/cli.label.txt
   :literal:

mad
---

.. include:: cli/cli.mad.txt
   :literal:

quantiles
---------

.. include:: cli/cli.quantiles.txt
   :literal:

slice
-----

.. include:: cli/cli.slice.txt
   :literal:

slope
-----

.. include:: cli/cli.slope.txt
   :literal:

std
---

.. include:: cli/cli.std.txt
   :literal:

threshold
---------

.. include:: cli/cli.threshold.txt
   :literal:

uncertainty
-----------

.. include:: cli/cli.uncertainty.txt
   :literal:
