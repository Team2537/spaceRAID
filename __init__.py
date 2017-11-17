"""
Takes an video file (very long) and slowly pulls the matches in the video out
and makes those seperate files.

Various possibilites and operations.
test, parse, finish, upload, run

spaceraid (run|parse|finish|upload|test) <input file> ... <output file/folder>
(global)
--version             Print version info and exit.
-v --verbose          Turn on verbose reporting.
-l --log file         Logging file.
-d --dryrun           Don't read any files or access internet. List what would
                      be done.

test      Run a test to see if the video is readable.
-i  --image_folder   For test, a folder of images can be specified instead of
                      a video.
-a  --answers        Actual results for the video so they can be compared to.

parse     Actually analyize the video file.

finish    Fixup the output video files. Add intro and fix name.
-t --tags [all|yellow|green]
                      Look at the eXtra tags and only finish tags tagged with
                      green and not red. Default is green. Yellow is will
                      process videos with yellow flags but not green.

upload    Upload the file to youtube.
run       Do parse, finish, and probably upload. Run will be done if no
          command is given.
"""
# Configure logging.
import logging

logging.basicConfig(
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

import sys
import argparse

parser = argparse.ArgumentParser()

##parser.add_argument('input_files', metavar='infile', type=int, nargs='+',
##                    help='an integer for the accumulator')

##parser.add_argument('--log-lvl', action='store', dest = 'logging_level',
##                    choices = ('CRITICAL', 'DEBUG', 'ERROR', 'FATAL', 'INFO',
##                               'NOTSET', 'WARN', 'WARNING', "NONE"),
##                    default = "DEBUG", help = "Change the logging level of data shown.")

parser.add_argument("-v", "--verbose",
                    help="increase output verbosity", action="store_true")

parser.add_argument('--version', action='version', version='%(prog)s 1.0')

# Subparsers / Operations
subparsers = parser.add_subparsers(
    dest = "operation", title = "Operations", metavar = "operation",
    description = "Processing operation to be taken.",
    help="Commands for spaceraid. Run is default.")

default = subparsers.add_parser("")
parser_run = subparsers.add_parser("run", help = (
    "Do parse, finish, and probably upload. Run will be done if no command "
    "is given."))

# This is the default.
##subparsers.default = parser_run
##parser.set_defaults(operation = parser_run)

parser_parse = subparsers.add_parser("parse", help = "Analyize the video(s).")

parser_finish = subparsers.add_parser("finish", help = (
    "Fixup the output video files. Add intro and fix name."))

parser_upload=subparsers.add_parser("upload",help="Upload the file to youtube.")

parser_test = subparsers.add_parser("test", help = (
    "Run a test to see if the video is readable."))

parser.add_argument('infile', nargs='+', type=argparse.FileType('r'),
                    default=sys.stdin)

parser.add_argument('outfile', type=argparse.FileType('w'))

results = parser.parse_args()

from pprint import pprint

pprint(results)
