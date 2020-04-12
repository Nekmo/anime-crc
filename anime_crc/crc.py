#!/usr/bin/env python3
"""

CRC32 generator and checker.

2018 Feb 25 v0.8

Requires Python 3.5+.

Copyright (c) 2009 Taoufik El Aoumari (forked from version 0.2, 2009-01-25)
Copyright (c) 2011-2018 Nekmo
Copyright (c) 2017-2018 Alicia Boya García (ntrrgc)

Original script: http://agafix.org/anime-crc32-checksum-in-linux-v20/
Modified by nekmo and ntrrgc to add several features:

- Add CRC32 codes to files
- More Pythonic code
- Fix size == 0 bug
- Logging
- Console arguments
- Compute CRC32 on files missing it without renaming them
- Customizable logging level
- Ported to Python3
- Recursive exploration
- Locale-aware sorting in recursive exploration
- Cleared progress output on exit
- Add option to remove CRC tags
- Add option to warn of missing tags
- Exit with status code 1 if there is a mismatch (be nice with scripts)
- File entries are written to stdout, progress to stderr
- Colors and progress reporting are disabled if not in a tty
- xattr store
- Add filter for commonly unwanted files and directories, such as .DS_Store

Released under the GPL license http://www.gnu.org/licenses/gpl-3.0.txt
"""

import locale
import logging
import os
import re
import sys
import zlib
from typing import Union, Tuple, List


locale.setlocale(locale.LC_ALL, "")
stdout_is_tty = os.isatty(sys.stdout.fileno())
stderr_is_tty = os.isatty(sys.stderr.fileno())


def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'

    class K:
        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0

    return K


# Colors
c_null = "\x1b[00;00m" if stdout_is_tty else ""
c_red = "\x1b[31;01m" if stdout_is_tty else ""
c_green = "\x1b[32;01m" if stdout_is_tty else ""

# Code to move 8 characters back in a tty
seq_backspace = "\x08" * 8 if stdout_is_tty else ""

# Code to delete 8 characters back in a tty (go back, fill with spaces, go back again)
clear_progress = seq_backspace + " " * 8 + seq_backspace if stdout_is_tty else ""

long_extensions = {".tar.gz", ".tar.bz", ".tar.xz"}


def split_file_extension(file_name: str) -> Tuple[str, str]:
    """
    Split the given file name as (base_name, extension).
    The extension either starts by dot or is empty string.
    """
    long_extension = next((
        ext
        for ext in long_extensions
        if file_name.endswith(ext)), None)
    if long_extension:
        base_name = file_name.rsplit(long_extension, 1)[0]
        return base_name, long_extension

    split_name = file_name.rsplit(".", 1)
    if len(split_name) == 1:
        # Handle dot-less files like "Makefile"
        return split_name[0], ""
    elif len(split_name) == 2 and split_name[0] == "":
        # Handle hidden files that start with dot, like ".directory".
        # We don't consider ".directory" an extension, but rather the base name.
        return split_name[1], ""
    else:
        # Handle normal extensions, like in "hello.txt"
        return split_name[0], "." + split_name[1]


class CRCStorageInterface(object):
    @property
    def name(self) -> str:
        raise NotImplementedError

    def get_declared_crc(self, file_name: str) -> Union[str, None]:
        """:return string or None, if not found."""
        raise NotImplementedError

    def set_declared_crc(self, file_name: str, hex_uppercase_crc: str) -> str:
        """:return new file name after setting the tag."""
        raise NotImplementedError

    def unset_declared_crc(self, file_name: str) -> Tuple[bool, str]:
        """:return whether a tag has been removed, file name after removing
        the tag """
        raise NotImplementedError

    def get_file_repr(self, file_name: str, match_color: str,
                      declared_hex_uppercase_crc: str) -> str:
        """Representation of the file name printed to the log."""
        raise NotImplementedError


class ChainCRCStorage:
    def __init__(self, stores: List[CRCStorageInterface]) -> None:
        self.stores = stores

    # Should return this, but PyCharm is not smart enough to handle it:
    # Union[Tuple[str, CRCStorageInterface], Tuple[None, None]]:
    def get_declared_crc_and_store(self, file_name: str) -> Tuple[
        Union[str, None], Union[CRCStorageInterface, None]]:
        for store in self.stores:
            crc = store.get_declared_crc(file_name)
            if crc:
                return crc, store
        return None, None

    def set_declared_crc(self, file_name: str, hex_uppercase_crc: str) -> str:
        for store in self.stores:
            file_name = store.set_declared_crc(file_name, hex_uppercase_crc)
        return file_name

    def unset_declared_crc(self, file_name: str) -> Tuple[bool, str]:
        removed_anything = False
        for store in self.stores:
            removed_this, file_name = store.unset_declared_crc(file_name)
            removed_anything = removed_anything or removed_this
        return removed_anything, file_name


class FileNameCRCStorage(CRCStorageInterface):
    name = 'filename'

    def get_file_repr(self, file_name: str, match_color: str,
                      declared_hex_uppercase_crc: str) -> str:
        before_crc, crc_portion, after_crc = re.match(
            r"^(.*\[)([a-fA-F0-9]{8})(\].*)$", file_name).groups()
        return "{before_crc}{match_color}{crc_portion}{c_null}{after_crc}".format(
            c_null=c_null, **locals())

    def get_declared_crc(self, file_name: str) -> Union[str, None]:
        match = re.match(r".*\[([a-fA-F0-9]{8})\].*", file_name)
        if match:
            return match.groups()[0].upper()
        else:
            return None

    def set_declared_crc(self, file_name: str, hex_uppercase_crc: str) -> str:
        directory = os.path.dirname(file_name)
        base_name = os.path.basename(file_name)

        name_part, extension = split_file_extension(
            self._name_without_crc(base_name))

        name_part_with_path = os.path.join(directory, name_part)
        name_pattern = '{name_part_with_path} [{hex_uppercase_crc}]{extension}'
        new_file_name = name_pattern.format(**locals())

        self._do_rename(file_name, new_file_name)
        return new_file_name

    @staticmethod
    def _name_without_crc(file_name: str) -> str:
        return re.sub(r" ?\[([a-fA-F0-9]{8})\]", "", file_name)

    @staticmethod
    def _do_rename(file_name: str, new_file_name: str) -> None:
        logging.info('%s -> %s' % (file_name, new_file_name))
        os.rename(file_name, new_file_name)

    def unset_declared_crc(self, file_name: str) -> Tuple[bool, str]:
        new_file_name = self._name_without_crc(file_name)
        if file_name != new_file_name:
            self._do_rename(file_name, new_file_name)
            return True, new_file_name
        else:
            return False, file_name


try:
    import xattr

    python_xattr_available = True
except ImportError:
    python_xattr_available = False


class XAttrCRCStorage(CRCStorageInterface):
    name = "xattr"

    def get_declared_crc(self, file_name: str) -> Union[str, None]:
        try:
            return xattr.getxattr(file_name, b"user.nekcrc").decode()
        except OSError:
            return None

    def set_declared_crc(self, file_name: str, hex_uppercase_crc: str) -> str:
        logging.info('%s (%s)' % (file_name, hex_uppercase_crc))
        xattr.setxattr(file_name, b"user.nekcrc", hex_uppercase_crc.encode())
        return file_name

    def unset_declared_crc(self, file_name: str) -> Tuple[bool, str]:
        try:
            xattr.removexattr(file_name, b"user.nekcrc")
            logging.info('%s (removed CRC xattr)' % file_name)
            return True, file_name
        except OSError:
            return False, file_name

    def get_file_repr(self, file_name: str, match_color: str,
                      declared_hex_uppercase_crc: str) -> str:
        return "{file_name} ({match_color}{declared_hex_uppercase_crc}{c_null})".format(
            c_null=c_null, **locals())


def compute_crc(filename, progress_reporting):
    """Calculate the CRC32 checksum of a file.
    Returns the CRC32 code as an hexadecimal string."""

    crc = 0
    file = open(filename, "rb")
    buff_size = 65536
    size = os.path.getsize(filename)
    done = 0

    if not size:
        # Empty file, quit
        logging.error('The file %s is empty' % filename)
        return

    while True:
        # While there is some data remaining...
        data = file.read(buff_size)
        done += len(data)
        if progress_reporting:
            # Show progress
            sys.stderr.write("%7d" % (done * 100 / size) + "%" + seq_backspace)
        if not data:
            # No more data, quit
            break
        crc = zlib.crc32(data, crc)

    file.close()

    return "%.8X" % crc


def check_files(files, warn_no_crc, read_from, progress_reporting) -> bool:
    """Check CRC32 for the provided file name list."""
    mismatch_found = False
    read_crc_storage = ChainCRCStorage(read_from)

    for file_name in files:
        try:
            # Find CRC32 within the file name
            declared_crc, store = read_crc_storage.get_declared_crc_and_store(
                file_name)
            if declared_crc is None:
                level = "warning" if warn_no_crc else "info"
                getattr(logging, level)(
                    '%s does not have a CRC tag' % file_name)
                continue

            # Calculate CRC32
            computed_crc = compute_crc(file_name, progress_reporting)
            if not computed_crc:
                continue  # empty file

            # Check the computed CRC32 matches the declared CRC32
            if computed_crc == declared_crc:
                match_color = c_green
                level = 'info'
            else:
                match_color = c_red
                level = 'warning'
                mismatch_found = True

            formatted_name = store.get_file_repr(file_name, match_color,
                                                 declared_crc)
            getattr(logging, level)("{match_color}{computed_crc}{c_null}  "
                                    "{formatted_name}".format(c_null=c_null,
                                                              **locals()))
        except IOError as e:
            logging.error(e)
            continue

    return mismatch_found


def add_crc32_tags(files, read_from, write_to, progress_reporting):
    """Add a CRC32 code to files missing it."""
    read_crc_storage = ChainCRCStorage(read_from)
    write_crc_storage = ChainCRCStorage(write_to)

    for file_name in files:
        try:
            # Try to read existing CRC32
            declared_crc, store = read_crc_storage.get_declared_crc_and_store(
                file_name)
            if declared_crc:
                store_name = store.name
                logging.debug("{file_name} already has a CRC declared with the '{store_name}' store.".format(**locals()))
                continue

            computed_crc = compute_crc(file_name, progress_reporting)
            if not computed_crc:
                continue

            file_name = write_crc_storage.set_declared_crc(file_name, computed_crc)

        except IOError as e:
            print(e)
            continue


def delete_crc32_tags(files, write_to):
    """Remove CRC32 codes to the specified files (danger!)"""
    write_crc_storage = ChainCRCStorage(write_to)
    for file_name in files:
        try:
            removed_anything, file_name = write_crc_storage.unset_declared_crc(file_name)
            if not removed_anything:
                logging.info("%s has no CRC tags to remove." % file_name)

        except IOError as e:
            print(e)
            continue


def separate_directories(file_list):
    directories = []
    files = []

    for file_name in file_list:
        if os.path.isdir(file_name):
            directories.append(file_name)
        else:
            files.append(file_name)

    return files, directories


ignore_dir_patterns = [
    re.compile(r"^@eaDir$"),
    re.compile(r"^\.Trash-[0-9]+$"),
    re.compile(r"^#recycle$"),
    re.compile(r"^__MACOSX$"),
]


ignore_file_patterns = [
    re.compile(r"^desktop\.ini$"),
    re.compile(r"^Thumbs\.db$"),
    re.compile(r"^\.DS_Store$"),
    re.compile(r"^\.directory$"),
]


def recurse_file_list(original_list, recurse_files):
    original_files, original_dirs = separate_directories(original_list)

    if not recurse_files:
        return original_files  # filter out directories

    found_files = []
    for rootdir in original_dirs:
        for root, sub_folders, files in os.walk(rootdir):
            files.sort(key=cmp_to_key(locale.strcoll))
            sub_folders.sort(key=cmp_to_key(locale.strcoll))

            sub_folders[:] = [
                folder for folder in sub_folders
                if not any(
                    pattern.match(folder)
                    for pattern in ignore_dir_patterns
                )
            ]

            for file in files:
                if any(pattern.match(file) for pattern in ignore_file_patterns):
                    continue
                f = os.path.join(root, file)
                found_files.append(f)

    return original_files + found_files


def parse_store_list(string_list: str) -> List[CRCStorageInterface]:
    stores = {
        "filename": FileNameCRCStorage,
        "xattr": XAttrCRCStorage,
    }

    ret = []
    for store_name in string_list.split(","):
        if store_name == "xattr" and not python_xattr_available:
            logging.info("Cannot use xattr store without python3-xattr.")
            raise SystemExit(2)

        ret.append(stores[store_name]())
    return ret
