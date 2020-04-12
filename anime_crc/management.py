import argparse
import logging
import sys

from anime_crc.crc import parse_store_list, python_xattr_available, stdout_is_tty, stderr_is_tty, ChainCRCStorage, \
    add_crc32_tags, recurse_file_list, delete_crc32_tags, check_files, clear_progress


def execute_from_command_line():
    parser = argparse.ArgumentParser(description='CRC32 generator and checker.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # addcrc32
    parser.add_argument('-a', '--addcrc32', dest='add_crc32_tags', nargs='*',
                        metavar='<file>',
                        help='Generate CRC32 for files and rename them.')

    parser.add_argument('--delete', dest='delete_crc32_tags', nargs='*',
                        metavar='<file>',
                        help='Delete CRC32 tags in the specified files.')

    # Recursive
    parser.add_argument('-r', '--recursive', dest='recursive',
                        action='store_const',
                        const=True, default=False,
                        help='Explore directories recursively.')
    # log level
    parser.add_argument('--debug', dest='level', action='store_const',
                        const=logging.DEBUG, default=logging.INFO,
                        help='Set log level to debugging messages.')
    parser.add_argument('--warning', dest='level', action='store_const',
                        const=logging.WARNING, default=logging.INFO,
                        help='Set log level to warnings (hides successful files).')

    parser.add_argument('--no-warn-missing-xattr-ext', action='store_const',
                        const=True, default=False,
                        help="Don't warn of missing python3-xattr optional dependency.")

    parser.add_argument('--warn-no-crc', action='store_const',
                        const=True, default=False,
                        help="Show a warning if no CRC tags are found in a file.")

    parser.add_argument('-n', '--no-progress', action='store_const',
                        const=True, default=False,
                        help="Disable progress reporting, even if connected to a tty.")

    # Stores
    parser.add_argument('--read-from', type=parse_store_list,
                        metavar='<stores>',
                        default="filename,xattr" if python_xattr_available else "filename",
                        help="A comma-separated list of tag stores used for checking integrity. "
                             "First successful read is used.")

    parser.add_argument('--write-to', type=parse_store_list,
                        metavar='<stores>',
                        default="filename",
                        help="A comma-separated list of tag stores used for writing CRC tags. "
                             "Tags are written in every tag store specified.")

    # check
    parser.add_argument('check', nargs='*', metavar='<file>',
                        help='Check CRC32 of files.')

    args = parser.parse_args()

    # Set log level
    logging.basicConfig(level=args.level, format='%(levelname)-8s %(message)s',
                        stream=sys.stdout)

    if not python_xattr_available and not args.no_warn_missing_xattr_ext:
        logging.warning(
            "python3-xattr is not installed, no 'xattr' store support.")

    recurse_files = args.recursive

    warn_no_crc = args.warn_no_crc

    progress_reporting = stdout_is_tty and stderr_is_tty and not args.no_progress

    exit_with_error = False
    try:
        if args.add_crc32_tags:
            # Add CRC32 to files
            add_crc32_tags(recurse_file_list(args.add_crc32_tags, recurse_files), args.read_from,
                           args.write_to, progress_reporting)

        if args.delete_crc32_tags:
            # Remove CRC32 tags
            delete_crc32_tags(recurse_file_list(args.delete_crc32_tags, recurse_files), args.write_to)

        if args.check:
            # Check files integrity against existing CRC32 tags
            exit_with_error = check_files(recurse_file_list(args.check, recurse_files), warn_no_crc,
                                          args.read_from, progress_reporting)

    except KeyboardInterrupt:
        # ^C was pressed in the terminal
        exit_with_error = True

    if progress_reporting:
        sys.stderr.write(clear_progress)

    if exit_with_error:
        raise SystemExit(1)
