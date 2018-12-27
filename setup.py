from setuptools import setup, find_packages


# Parse the version from the shapely module
for line in open('terrain/__init__.py', 'r'):
    if line.find("__version__") >= 0:
        version = line.split("=")[1].strip()
        version = version.strip('"')
        version = version.strip("'")
        continue

with open('VERSION.txt', 'w') as fp:
    fp.write(version)

setup(name='rio-terrain',
      version=version,
      author='Michael Rahnis',
      author_email='michael.rahnis@fandm.edu',
      description='Rasterio CLI plugin to perform common operations on height rasters.',
      url='http://github.com/mrahnis/rio-terrain',
      license='BSD',
      packages=find_packages(exclude=['examples']),
      include_package_data=True,
      install_requires=[
        'numpy',
        'scipy',
        'matplotlib',
        'rasterio',
        'click',
        'crick',
      ],
      entry_points='''
        [rasterio.rio_commands]
        aspect=terrain.cli.aspect:aspect
        curvature=terrain.cli.curvature:curvature
        difference=terrain.cli.difference:difference
        extract=terrain.cli.extract:extract
        mad=terrain.cli.mad:mad
        quantiles=terrain.cli.quantiles:quantiles
        slice=terrain.cli.slice:slice
        slope=terrain.cli.slope:slope
        std=terrain.cli.std:std
        threshold=terrain.cli.threshold:threshold
        uncertainty=terrain.cli.uncertainty:uncertainty
      ''',
      keywords='LiDAR, surveying, elevation, raster, DEM',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: GIS'
      ])
