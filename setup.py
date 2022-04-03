from setuptools import setup, find_packages
import versioneer


with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f]

setup(name='rio-terrain',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      author='Michael Rahnis',
      author_email='mike@topomatrix.com',
      description='Rasterio CLI plugin to perform common operations on single-band elevation rasters',
      long_description=long_description,
      long_description_content_type='text/x-rst',
      url='http://github.com/mrahnis/rio-terrain',
      license='BSD',
      packages=find_packages(exclude=['examples']),
      include_package_data=True,
      install_requires=requirements,
      entry_points='''
        [rasterio.rio_commands]
        aspect=rio_terrain.cli.aspect:aspect
        labelbounds=rio_terrain.cli.labelbounds:labelbounds
        compare=rio_terrain.cli.compare:compare
        copynodata=rio_terrain.cli.copynodata:copynodata
        curvature=rio_terrain.cli.curvature:curvature
        difference=rio_terrain.cli.difference:difference
        extract=rio_terrain.cli.extract:extract
        fillnodata=rio_terrain.cli.fillnodata:fillnodata
        label=rio_terrain.cli.label:label
        mad=rio_terrain.cli.mad:mad
        quantiles=rio_terrain.cli.quantiles:quantiles
        slice=rio_terrain.cli.slice:slice
        slope=rio_terrain.cli.slope:slope
        std=rio_terrain.cli.std:std
        subdivide=rio_terrain.cli.subdivide:subdivide
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
