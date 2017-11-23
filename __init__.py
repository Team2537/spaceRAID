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

# WARNING, this is not stable unless the current directory is the directory
# with this file.
import os # Needed anyway
import inspect

try:
    assert os.path.samefile(
        os.path.dirname(inspect.getfile(inspect.currentframe())),
        os.getcwd())
except:
    print("File %r" % os.path.dirname(inspect.getfile(inspect.currentframe())))
    print("pwd  %r" % os.getcwd())
    raise

import sys
import logging
import argparse

logging.basicConfig(
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

try:
    # Cv2 and ffmpeg can be broken.
    import find_matches
    import process_frames
    import video_loader # This should be removed at some point.
except ImportError:
    sys.stderr.write(
        "ImportError, cv2 or ffmpeg are not installed or corrupted.\n"
        "Please reinstall.\n")
    exit(1)

from pprint import pprint

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

QUITE_UNKNOWN_ERROR = False
#################################### Parser ####################################
parser = argparse.ArgumentParser(prog = "spaceraid")

parser.add_argument("-q", "--quiet", dest = "log_level", action = "store_const",
                    const = logging.ERROR, help="Make the output less verbose"
                    "with only important information. (Default).")

parser.add_argument("-v", "--verbose", dest = "log_level", action="store_const",
                    const = logging.DEBUG, help="Make the output verbose.")

parser.set_defaults(log_level = logging.ERROR)

parser.add_argument("--version",action="version",version="%(prog)s "+__version__)

parser.add_argument("-d", "--dryrun", action = "store_true", default = False,
                    help = "Don't read any files or access the internet. "
                           "List what would be done.")

parser.add_argument("-l", "--log", "--log_file", type = PathType(exists = None),
                    default='-', help =
                    "Logging file for all debug info from logging.")

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

# Disable these arguments.
# Though it works for the help menu, this is not functional.
# The problem is that "source_files" can not be an adjustable number of
# arguments. Because of the regex expressions set up by
# ArgumentParser._get_nargs_pattern() and executed in
# ArgumentParser._match_arguments_partial() would give all but the first
# specified files for "source_files" to the subparser for the subcommand.
#
# Specifically, the problem is in ArgumentParser._get_nargs_pattern() line,
# argparse (lineno 2183)
#2181           # allow one argument followed by any number of options or arguments
#2182           elif nargs == PARSER:
#2183 ->            nargs_pattern = '(-*A[-AO]*)'
#2184
# The problem here is that the parser regex expression is greedy. It will
# consume all arguments that are not reserved (like if source_files had nargs=2)
# for the subparser when the expression is evaluated at
# ArgumentParser._match_arguments_partial() (lineno 2047).
#
# Spefically, with "source_files" set to "+", the pattern in
# ArgumentParser._match_arguments_partial()
# pattern = '(-*A[-AO]*)(-*A[A-]*)(-*A-*)'
# arg_strings_pattern = 'AAAA'
# re.match(pattern, arg_strings_pattern).groups() -> ('AA', 'A', 'A')
#
# And for "source_files" is set to 2, the pattern in
# ArgumentParser._match_arguments_partial()
# pattern = '(-*A[-AO]*)(-*A-*A-*)(-*A-*)'
# arg_strings_pattern = 'AAAA'
# re.match(pattern, arg_strings_pattern).groups() -> ('A', 'AA', 'A')
#
# A possible fix would be to make a subclass of
# ArgumentParser._get_nargs_pattern() that made the parser pattern non-greedy.
# While this solution would solve this problem, it would give unexpected
# behavior if non-positional arguments were specified after a subparser.
# Additionally, this does not completely solve my problem because it really is
# not the best set-up for having these arguments anyway. For example, neither
# upload, nor test would make the best use of these arguments as neither would
# have an output and test my want a folder for an input. Additionally, it may
# make more since for the test's specific arguments to be entered AFTER the
# input file.
#
# The other possible fix is to either hardcode the files into the majority of
# the subparsers, or use the parents method to add them quickly to multiple
# parsers. The parents may work, but I would need to do more testing to
# determine if they actually fill allow for the positional and non-positional
# arguments to be specified in a logical order. The hardcode options would
# most definitely work, but would require code duplication.
#
# The real problem with either of these solutions is it means that no mention
# of how to specify arguments it given automatically in the help or usage.
# Here is example of what the help would look like with parents.
#
# >>> parent = argparse.ArgumentParser(add_help=False)
# >>> parent.add_argument('files', nargs = "+", action = "append")
# _AppendAction(option_strings=[], dest='files', nargs='+', const=None,
# default=None, type=None, choices=None, help=None, metavar=None)
# >>> subparsers = parser.add_subparsers()
# >>> subparsers.add_parser('test', parents = [parent])
# ArgumentParser(prog=' test', usage=None, description=None, version=None,
# formatter_class=<class 'argparse.HelpFormatter'>, conflict_handler='error',
# add_help=True)
# >>> parser.parse_args(['test', 'test1', 'test2'])
# Namespace(files=[['test1', 'test2']])
# >>> parser.parse_args(['test', '-h', 'test1', 'test2'])
# usage:  test [-h] files [files ...]
#
# positional arguments:
#   files
#
# optional arguments:
#   -h, --help  show this help message and exit
# >>> parser.parse_args(['-h'])
# usage: [-h] {test} ...
#
# positional arguments:
#   {test}
#
# optional arguments:
#   -h, --help  show this help message and exit
#
# So in-addition to these methods, rewriting of the help formatter would be
# required to make these solutions work. Otherwise, I guess I could live with
# the rather unhelpful help menu and just go let the thing work.
#
# That said, the nice simple solution that will work for now is to not use
# differing number of arguments in for the source files. By restricting
# nargs to 1, everything will work find for now.
#
# Some related problems are detailed here: https://bugs.python.org/issue9338
#
# Also, just as some debugging infomation, here are all of the places that the
# args was checked in argparse when this was run. This was done by overriding
# the __eq__ method on the narg varible. It is possible that some other test
# was used that was not caught, but it looks unlikely.
# Execution pattern of nargs = "+"
# argparse.py  2166 Compared eq + to      ? (False).
# argparse.py  2170 Compared eq + to      * (False).
# argparse.py  2174 Compared eq + to      + (True).
# argparse.py  2202 Compared eq + to   A... (False).
# argparse.py  2202 Compared eq + to    ... (False).
# argparse.py  2229 Compared eq + to   None (NotImplemented).
# argparse.py  2229 Compared eq + to      ? (False).
# argparse.py  2235 Compared eq + to    ... (False).
# argparse.py  2239 Compared eq + to   A... (False).
# TEST -
# TEST example_folder
# TEST -
# argparse.py   577 Compared eq + to      ? (False).
# argparse.py   579 Compared eq + to      * (False).
# argparse.py   581 Compared eq + to      + (True).
# argparse.py   577 Compared eq + to      ? (False).
# argparse.py   579 Compared eq + to      * (False).
# argparse.py   581 Compared eq + to      + (True).
# argparse.py   577 Compared eq + to      ? (False).
# argparse.py   579 Compared eq + to      * (False).
# argparse.py   581 Compared eq + to      + (True).
# argparse.py   577 Compared eq + to      ? (False).
# argparse.py   579 Compared eq + to      * (False).
# argparse.py   581 Compared eq + to      + (True).

parser.add_argument('source_files',nargs=1,action ="append",
                    type=PathType(dash_ok=False), # Turns out opencv won't do -.
                    help = "Video file to analyze.")
# All this fuss, for this one line.

parser.add_argument('target_dir', type = PathType(type='dir', exists = None),
                    help = "Output folder for processed videos.")

def main(args=None):
    results = parser.parse_args(args)

    # Flatten the source_files varible to just be a list of files.
    # Not a concentric list of files.
    results.source_files = sum(results.source_files, [])
    pprint(vars(results))

    # -l implementation.
    logging.getLogger().setLevel(results.log_level)
    logging.info("Passed args: %r" % args)

    try:
        results.operation(results)
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt")
        parser.exit(130, "Keyboard Interrupt")
    except:
        # Any error, including Keyboard, print something and exit.
        logging.exception(sys.exc_info()[1])
        if QUITE_UNKNOWN_ERROR:
            parser.error(sys.exc_info()[1])
        else:
            # Don't give a nice clean exit code. There has been an error, crash.
            raise

if __name__ == '__main__':
    main() #main(['parse', '-', '-', 'example_folder'])
