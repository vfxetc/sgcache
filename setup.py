from setuptools import setup, find_packages

setup(

    name='sgcache',
    version='0.1-dev',
    description='A site-local Shotgun cache',
    url='http://github.com/westernx/sgcache',
    
    packages=find_packages(exclude=['build*', 'tests*']),
    
    author='Mike Boers',
    author_email='sgcache@mikeboers.com',
    license='BSD-3',
    
    install_requires=[
        # TODO: a few things go here
    ],

    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    
)
