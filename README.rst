.. image:: https://raw.githubusercontent.com/Nekmo/anime-crc/master/logo.png
    :width: 100%

|


.. image:: https://img.shields.io/travis/Nekmo/anime-crc.svg?style=flat-square&maxAge=2592000
  :target: https://travis-ci.org/Nekmo/anime-crc
  :alt: Latest Travis CI build status

.. image:: https://img.shields.io/pypi/v/anime-crc.svg?style=flat-square
  :target: https://pypi.org/project/anime-crc/
  :alt: Latest PyPI version

.. image:: https://img.shields.io/pypi/pyversions/anime-crc.svg?style=flat-square
  :target: https://pypi.org/project/anime-crc/
  :alt: Python versions

.. image:: https://img.shields.io/codeclimate/github/Nekmo/anime-crc.svg?style=flat-square
  :target: https://codeclimate.com/github/Nekmo/anime-crc
  :alt: Code Climate

.. image:: https://img.shields.io/codecov/c/github/Nekmo/anime-crc/master.svg?style=flat-square
  :target: https://codecov.io/github/Nekmo/anime-crc
  :alt: Test coverage

.. image:: https://img.shields.io/requires/github/Nekmo/anime-crc.svg?style=flat-square
     :target: https://requires.io/github/Nekmo/anime-crc/requirements/?branch=master
     :alt: Requirements Status

#########
anime-crc
#########

Validate and create CRC checksums for files (ex. ```anime video [ABCD01234].mkv```)

To **install anime-crc**, run this command in your terminal:

.. code-block:: console

    $ sudo pip install anime-crc

This is the preferred method to install anime-crc, as it will always install the most recent stable release.

Usage
=====
Show anime-crc help running::

    $ anime-crc -h

The output with the current release is:

.. code-block::

    usage: anime-crc [-h] [-a [<file> [<file> ...]]] [--delete [<file> [<file> ...]]] [-r] [--debug] [--warning] [--no-warn-missing-xattr-ext] [--warn-no-crc] [-n] [--read-from <stores>] [--write-to <stores>] [<file> [<file> ...]]

    CRC32 generator and checker.

    positional arguments:
      <file>                Check CRC32 of files. (default: None)

    optional arguments:
      -h, --help            show this help message and exit
      -a [<file> [<file> ...]], --addcrc32 [<file> [<file> ...]]
                            Generate CRC32 for files and rename them. (default: None)
      --delete [<file> [<file> ...]]
                            Delete CRC32 tags in the specified files. (default: None)
      -r, --recursive       Explore directories recursively. (default: False)
      --debug               Set log level to debugging messages. (default: 20)
      --warning             Set log level to warnings (hides successful files). (default: 20)
      --no-warn-missing-xattr-ext
                            Don't warn of missing python3-xattr optional dependency. (default: False)
      --warn-no-crc         Show a warning if no CRC tags are found in a file. (default: False)
      -n, --no-progress     Disable progress reporting, even if connected to a tty. (default: False)
      --read-from <stores>  A comma-separated list of tag stores used for checking integrity. First successful read is used. (default: filename)
      --write-to <stores>   A comma-separated list of tag stores used for writing CRC tags. Tags are written in every tag store specified. (default: filename)


Features
========

* **Check CRC** of files. The checksum can be in the filename (ex. ``[ABCD01234]``), in a separate file or in the
  file metadatas (*xattr*).
* **Set CRC** of files. The CRC can be written to the name, to a separate file or to file metadatas.
* **Delete CRC** of file names.
