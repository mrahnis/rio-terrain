===========
rio-terrain
===========

Rio-terrain provides a set of rasterio CLI plugins to perform common raster operations, and can write slope, aspect and curvature rasters.

.. image:: https://github.com/mrahnis/rio-terrain/workflows/Python%20package/badge.svg
	:target: https://github.com/mrahnis/rio-terrain/actions?query=workflow%3A%22Python+package%22
	:alt: Python Package

.. image:: https://github.com/mrahnis/rio-terrain/workflows/Conda%20package/badge.svg
	:target: https://github.com/mrahnis/rio-terrain/actions?query=workflow%3A%22Conda+package%22
	:alt: Conda Package

.. image:: https://readthedocs.org/projects/rio-terrain/badge/?version=latest
	:target: http://rio-terrain.readthedocs.io/en/latest/?badge=latest
	:alt: Documentation Status

.. image:: https://coveralls.io/repos/github/mrahnis/rio-terrain/badge.svg?branch=main
	:target: https://coveralls.io/github/mrahnis/rio-terrain?branch=main

Installation
============

.. image:: https://img.shields.io/pypi/v/rio-terrain.svg
   :target: https://pypi.python.org/pypi/rio-terrain/

.. image:: https://anaconda.org/mrahnis/rio-terrain/badges/version.svg
	:target: https://anaconda.org/mrahnis/rio-terrain

To install from the Python Package Index:

.. code-block:: console

	$pip install rio-terrain

To install from Anaconda Cloud:

If you are starting from scratch the first thing to do is install the Anaconda Python distribution, add the necessary channels to obtain the dependencies and install rio-terrain.

.. code-block:: console

	$conda config --append channels conda-forge
	$conda install rio-terrain -c mrahnis

To install from the source distribution execute the setup script in the rio-terrain directory:

.. code-block:: console

	$python setup.py install

Examples
========

TODO

License
=======

BSD

Documentation
=============

Latest `html`_

.. _html: http://rio-terrain.readthedocs.org/en/latest/