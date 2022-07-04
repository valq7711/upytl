import re
from setuptools import setup


def get_module_var(varname):
    src = 'upytl'
    regex = re.compile(fr"^{varname}\s*\=\s*['\"](.+?)['\"]", re.M)
    mobj = next(regex.finditer(open(f"{src}/__init__.py").read()))
    return mobj.groups()[0]


__author__ = get_module_var('__author__')
__license__ = get_module_var('__license__')
__version__ = get_module_var('__version__')


setup(
    name="upytl",
    version=__version__,
    url="https://github.com/valq7711/upytl",
    license=__license__,
    author=__author__,
    author_email="valq7711@gmail.com",
    maintainer=__author__,
    maintainer_email="valq7711@gmail.com",
    description="UPYTL - Ultra Pythonic Template Language",
    platforms="any",
    keywords='python webapplication html',
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Markup :: HTML",
    ],
    python_requires='>=3.7',
    packages=['upytl'],
)
