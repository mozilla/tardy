from setuptools import setup

setup(
    name='tardy',
    version='0.1.7',
    description='Update services on stackato',
    author='Andy McKay',
    author_email='andym@mozilla.com',
    license='MPL 2.0',
    packages=['tardy'],
    entry_points={
        'console_scripts': [
            'tardy = tardy.cmd:main'
        ]
    },
)
