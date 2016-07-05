from distutils.core import setup

setup(
    name='chimera-vaisala',
    version='0.0.1',
    packages=['chimera_vaisala', 'chimera_vaisala.instruments'],
    scripts=[],
    url='http://github.com/astroufsc/chimera-vaisala',
    license='GPL v2',
    author='William Schoenell',
    author_email='william@iaa.es',
    description='Vaisala weather transmitters chimera plugin'
)
