#!/usr/bin/env python
"""
Takes an video file (very long) and slowly pulls the matches in the video out
and makes those seperate files.

Various possibilites and operations.
test, parse, finish, upload, run

spaceraid {run,parse,finish,upload,test} source_file ... target_dir
(global)
--help
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
          command is given if I can figure out how to add that.
"""
__version__ = "1.0"

import sys
import logging
import argparse

logging.basicConfig(
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

import find_matches
import video_loader # This should be removed at some point.

# ==============
# Type classes
# PathType
# This is meant to allow for verifcation the passed argument is a path, but
# not opening a file immediatly.
# This can be useful for multiple things.
# - 1) In case of error, such as from a file that is read in, the program can
#      exist without having ever created an output file.
# - 2) Can be used to specify
# ==============

# Code taken from https://stackoverflow.com/questions/11415570/directory-path-types-with-argparse
# This is EXACTLY what I was going to build otherwise.
# This is also suggested to be an official change to argparse.
# https://mail.python.org/pipermail/stdlib-sig/2015-July/000990.html

# Added callable function, instead of __call__ check, and changed err to
# ArgumentTypeError. Also fixed os.path.sympath reference to os.path.islink.
import os
from argparse import ArgumentTypeError

class PathType(object):
    def __init__(self, exists=True, type='file', dash_ok=True):
        '''exists:
                True: a path that does exist
                False: a path that does not exist, in a valid parent directory
                None: don't care
           type: file, dir, symlink, None, or a function returning True for valid paths
                None: don't care
           dash_ok: whether to allow "-" as stdin/stdout'''

        assert exists in (True, False, None)
        assert type in ('file','dir','symlink',None) or callable(type)

        self._exists = exists
        self._type = type
        self._dash_ok = dash_ok

    def __call__(self, string):
        if string=='-':
            # the special argument "-" means sys.std{in,out}
            if self._type == 'dir':
                raise ArgumentTypeError('standard input/output (-) not allowed as directory path')
            elif self._type == 'symlink':
                raise ArgumentTypeError('standard input/output (-) not allowed as symlink path')
            elif not self._dash_ok:
                raise ArgumentTypeError('standard input/output (-) not allowed')
            return string # No reason to check anything else if this works.

        exists = os.path.exists(string)
        if self._exists == True:
            if not exists:
                raise ArgumentTypeError("path does not exist: '%s'" % string)

            if self._type is None:
                pass
            elif self._type=='file':
                if not os.path.isfile(string):
                    raise ArgumentTypeError("path is not a file: '%s'" % string)
            elif self._type=='symlink':
                if not os.path.islink(string):
                    raise ArgumentTypeError("path is not a symlink: '%s'" % string)
            elif self._type=='dir':
                if not os.path.isdir(string):
                    raise ArgumentTypeError("path is not a directory: '%s'" % string)
            elif not self._type(string):
                raise ArgumentTypeError("path not valid: '%s'" % string)
        else:
            if self._exists == False and exists:
                raise ArgumentTypeError("path exists: '%s'" % string)

            p = os.path.dirname(os.path.normpath(string)) or '.'
            if not os.path.isdir(p):
                raise ArgumentTypeError("parent path is not a directory: '%s'" % p)
            elif not os.path.exists(p):
                raise ArgumentTypeError("parent directory does not exist: '%s'" % p)

        return string

#################################### Parser ####################################
parser = argparse.ArgumentParser(prog = "spaceraid")

parser.add_argument("-q", "--quiet", dest = "log_level", action = "store_const",
                    const = logging.ERROR, help="Make the output less verbose"
                    "with only important information. (Default).")

parser.add_argument("-v", "--verbose", dest = "log_level", action="store_const",
                    const = logging.DEBUG, help="Make the output verbose.")

parser.set_defaults(log_level = logging.ERROR)

parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

parser.add_argument("-d", "--dryrun", action = "store_true", default = False,
                    help = "Don't read any files or access the internet. "
                           "List what would be done.")

parser.add_argument("-l","--log","--log_file",type=PathType(exists=None),default='-',
                    help = "Logging file for all debug info from logging.")

# Subparsers / Operations
subparsers = parser.add_subparsers(
    dest = "operation_name", title = "Operations",
    description = "Processing operation to be taken.",
    help="Commands for %(prog)s. Run is default.")

##################################### Run ######################################
parser_run = subparsers.add_parser("run", help = \
    "Do parse, finish, and upload. Run will be done if no command is given.")

# This should be the default. I just have to
# figured out how to do that.
##subparsers.default = parser_run
##parser.set_defaults(operation = parser_run)
##default = subparsers.add_parser("")

def run(namespace):
    """Run operation for spaceraid."""
    raise NotImplementedError("Haven't run finish yet.")

parser_run.set_defaults(operation = run)

del parser_run # No need to keep varible.
#################################### Parse #####################################
parser_parse = subparsers.add_parser("parse", help = "Analyze the video(s).")

def parse(namespace):
    """Parse operation for spaceraid."""
##    raise NotImplementedError("Haven't made parse yet.")
    try:
        process_frames.init()

        for f in namespace.source_files:
            if not os.path.isfile(f):
                logging.error("File %r does not exists." % f)

            try:
                video = video_loader.Video(f)
                
                results = find_matches.scan_video(video)
                # Close the windows.
                process_frames.deinit()
                timings = find_matches.time_video(results)
                find_matches.write_files(video, timings)
            except ValueError:
                # The file stopped existing. Error.
                raise IOError("Video stopped existing while opening.")
            finally:
                video_loader.close_image()
    finally:
        process_frames.deinit()

parser_parse.set_defaults(operation = parse)

del parser_parse # No need to keep varible.
#################################### Finish ####################################
# -t --tags [all|yellow|green]                                                 #
#     Look at the eXtra tags and only finish tags tagged with                  #
#     green and not red. Default is green. Yellow is will                      #
#     process videos with yellow flags but not green.                          #

parser_finish = subparsers.add_parser("finish", help = (
    "Fixup the output video files. Add intro and fix name."))

parser_finish.add_argument(
    "-t","--tags",choices=("all","yellow","green"),default = "green",
    help = ("Look at the eXtra tags and only finish tags tagged with"
            "green and not red. Default is green. Yellow is will"
            "process videos with yellow flags but not green."))

def finish(namespace):
    """Finish operation for spaceraid."""
    raise NotImplementedError("Haven't made finish yet.")

parser_finish.set_defaults(operation = finish)
del parser_finish # No need to keep varible.
##################################### Run ######################################
parser_upload=subparsers.add_parser("upload",help="Upload the file to youtube.")

def upload(namespace):
    """Upload operation for spaceraid."""
    raise NotImplementedError("Haven't made upload yet.")

parser_upload.set_defaults(operation = upload)
del parser_upload # No need to keep varible.
##################################### Test #####################################
parser_test = subparsers.add_parser("test", help = (
    "Run a test to see if the video is readable."))

###This would require more effort to implement than I think is worth.
##parser_test.add_argument("-i", "--image_folder", type = PathType(type='dir'))

parser_test.add_argument("-a", "--answers", dest = "answers_file",
                         type = PathType(), help = \
    "Actual results for the video so they can be compared to."
    "This should be a cvs file with frame #, name, time.")

def test(namespace):
    """Test operation for spaceraid."""
    raise NotImplementedError("Haven't made test yet.")

parser_test.set_defaults(operation = test)
del parser_test
################################################################################
parser.add_argument('source_files', nargs='+', action = "append", type= PathType(),
                    help = "Video file to analyze.")

parser.add_argument('target_dir', type = PathType(type='dir', exists = None),
                    help = "Output folder for processed videos.")

def main(args=None):
    results = parser.parse_args(args)
    print(results)

    # -l implementation.
    logging.getLogger().setLevel(results.log_level)
    logging.info("Passed args: %r" % args)

    try:
        results.operation(results)
    except KeyboardInterrupt:
        logging.exception(sys.exc_value)
        parser.exit(130, sys.exc_value)
    except:
        # Any error, including Keyboard, print something and exit.
        logging.error(sys.exc_value)
        parser.error(sys.exc_value)
        

if __name__ == '__main__':
    main()
