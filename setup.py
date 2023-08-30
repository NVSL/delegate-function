from setuptools import setup, find_packages
import subprocess
import os, sys
import platform

with open("VERSION") as f:
    version = f.read()
    
setup(
    name="delegate_function",
    version=version.strip(),
    package_data={
        'delegate_function': ['VERSION'],
    },
    description="Running methods in other processes.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',   # Again, pick a license
        'Programming Language :: Python :: 3', 
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    url="https://github.com/NVSL/delegate-function",
    author="Steven Swanson",
    author_email="swanson@cs.ucsd.edu",
    py_modules=["delegate_function"],
    install_requires=["pytest-explicit"],
    entry_points={
        'console_scripts' :[
            'delegate-function-run=delegate_function:delegate_function_run'
        ]
    },
    
)


