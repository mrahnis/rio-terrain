from setuptools import setup, find_packages


for line in open('rio_terrain/__init__.py', 'r'):
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
        aspect=rio_terrain.cli.aspect:aspect
        curvature=rio_terrain.cli.curvature:curvature
        difference=rio_terrain.cli.difference:difference
        extract=rio_terrain.cli.extract:extract
        label=rio_terrain.cli.label:label
        mad=rio_terrain.cli.mad:mad
        quantiles=rio_terrain.cli.quantiles:quantiles
        slice=rio_terrain.cli.slice:slice
        slope=rio_terrain.cli.slope:slope
        std=rio_terrain.cli.std:std
        threshold=rio_terrain.cli.threshold:threshold
        uncertainty=rio_terrain.cli.uncertainty:uncertainty
      ''',
      keywords='LiDAR, surveying, elevation, raster, DEM',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: GIS'
      ])
