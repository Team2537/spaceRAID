#!/usr/bin/env python3
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
__author__ = "Matthew Schweiss and Rohan Uttamsingh"
__version__ = "1.1"

# WARNING, this is not stable unless the current directory is the directory
# with this file.
import os # Needed anyway
import inspect

try:
    assert os.path.samefile(
        os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))),
                        os.getcwd())
except:
    print("File %r" % os.path.dirname(inspect.getfile(inspect.currentframe())))
    print("pwd  %r" % os.getcwd())
    raise

import sys
import json
import time
import xattr
import logging
import argparse
import subprocess

logging.basicConfig(
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')

try:
    # Cv2 and ffmpeg can be broken.
    import find_matches
    import process_frames
    import video_loader # This should be removed at some point.
    import test_reader
except ImportError:
    sys.stderr.write(
        "ImportError, cv2 or ffmpeg are not installed or corrupted.\n"
        "Please reinstall.\n")
    sys.exit(1)

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
           dash_ok: whether to allow "-" as stdin/stdout
        '''

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
                raise ArgumentTypeError("parent path is not a directory: %r" % p)
            elif not os.path.exists(p):
                raise ArgumentTypeError("parent directory does not exist: %r" % p)

        return string

# For finish path walking.
# Partially from https://stackoverflow.com/questions/229186/os-walk-without-digging-into-directories-below
# Edited.
def walklevel(path, depth = 1):
    """It works just like os.walk, but you can pass it a level parameter
       that indicates how deep the recursion will go.
       If depth is -1 (or less than 0), the full depth is walked.
    """
    # if depth is negative, just walk
    if depth < 0:
        for root, dirs, files in os.walk(path):
            yield root, dirs, files

    # path.count works because is a file has a "/" it will show up in the list
    # as a ":"
    path = path.rstrip(os.path.sep)
    num_sep = path.count(os.path.sep)
    for root, dirs, files in os.walk(path):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + depth <= num_sep_this:
            del dirs[:]

MATCH_DATA_FILE = "match_results.json"
#################################### Parser ####################################
parser = argparse.ArgumentParser(prog = "spaceraid")

parser.add_argument("-q", "--quiet", dest = "log_level", action = "store_const",
                    const = logging.ERROR, help="Make the output less verbose"
                    "with only important information. (Default).")

parser.add_argument("-v", "--verbose", dest = "log_level", action="store_const",
                    const = logging.DEBUG, help="Make the output verbose.")

parser.set_defaults(log_level = logging.ERROR)

parser.add_argument("--version",action="version",version="%(prog)s "+__version__)

parser.add_argument("-l", "--log", "--log-file", type = PathType(exists = None),
                    default="-", help =
                    "Logging file for all debug info from logging.")

parser.add_argument("-d", "--data-log", type = PathType(exists = None))

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
    try:
        process_frames.init()

        for f in namespace.source_files:
            if not os.path.isfile(f):
                logging.error("File %r does not exists." % f)

            try:
                video = video_loader.Video(f)

                results = find_matches.scan_video(video)
                # Close the windows.
                video_loader.close_image()
                timings = find_matches.time_video(results)
                find_matches.write_files(video, timings)
            except ValueError:
                # The file stopped existing. Error.
                raise IOError("Video stopped existing while opening.")
            finally:
                video_loader.close_image()
    finally:
        process_frames.deinit() # Close the threading even on error.

parser_run.set_defaults(operation = run)

del parser_run # No need to keep varible.
#################################### Parse #####################################
parser_parse = subparsers.add_parser("parse", help = "Analyze the video(s).")

def parse(namespace):
    """Parse operation for spaceraid."""
    try:
        process_frames.init()

        for f in namespace.source_files:
            if not os.path.isfile(f):
                logging.error("File %r does not exists." % f)

            try:
                try:
                    video = video_loader.Video(f)
                except ValueError:
                    # The file stopped existing. Error.
                    raise IOError("Video stopped existing while opening.")

                global results
                results = find_matches.scan_video(video, get_data_log(namespace))

                video_loader.close_image()
                # Write the results to file.
                out_dir = namespace.target_dir
                if not os.path.exists(out_dir):
                    # Make the directory.
                    os.mkdir(out_dir)
                    logging.debug("Created folder %r" % out_dir)
                    data_file = os.path.join(out_dir, MATCH_DATA_FILE)
                elif os.path.isdir(out_dir):
                    # Then store the file at "match_results.json"
                    data_file = os.path.join(out_dir, MATCH_DATA_FILE)
                else:
                    data_file = None
                    raise ValueError("No data_file.")
                if data_file:
                    with open(data_file, "w") as out_file:
                        # Without other data, use str to serialize.
                        json.dump(results, out_file, default=str, indent=True)
            finally:
                video_loader.close_image()
    finally:
        process_frames.deinit() # Close the threading even on error.

    # Finished Processing!
    # Now save videos.
    timings = find_matches.time_video(results)
    find_matches.write_files(video, timings)

parser_parse.set_defaults(operation = parse)

del parser_parse # No need to keep varible.
#################################### Finish ####################################
# -t --tags [all|yellow|green]                                                 #
#     Look at the eXtra tags and only finish tags tagged with                  #
#     green and not red. Default is green. Yellow is will                      #
#     process videos with yellow flags but not green.                          #

parser_finish = subparsers.add_parser("finish", help =
    "Fixup the output video files. Add intro and fix name.")

parser_finish.add_argument(
    "-t","--tags",choices=("All","Yellow","Green"),default = "Green",
    help = ("Look at the eXtra tags and only finish tags tagged with"
            "green and not red. Default is green. Yellow is will"
            "process videos with yellow flags but not green."))
# Need to allow folders for this to be of use.
parser_finish.add_argument("-r","--recurse",action="store_true",default=False,
                           help="Recursively apply to videos in the directory.")

# A setable depth for recurse, implies -r
parser_finish.add_argument("-d","--depth",action="store",type=int,default=None,
                           help="Recursize depth of the specified folders.\n"
                               "Implies -r")

##def ffmpeg_command(text, output):
##    # Command to finish the video.
##    return ['/usr/local/Cellar/ffmpeg/3.4.1/bin/ffmpeg',
##            '-n', # Don't overwrite files.
##            '-hide_banner', # Just hide the banner, don't show that.
##            # This line appears to break everything.
##            '-loglevel', 'warning', # Less output
##            '-i', "Video Intro.mov", # Get Template Intro
##            '-vf', # Add a video filter for the text.
##
##            r'drawtext=fontfile=/Library/Fonts/Trebuchet\ MS.ttf: ' # Font
##            'text=%r: ' % text + # The changing text.
##            "enable='between(t,3,9)':" # Show only from 3s to 9s.
##            'fontcolor=white:' # White text
##            'fontsize=36:' # 36 Point Font.
##            'x=text_w/16:' # Text is left justified on the left.
##            'y=(h-text_h)/2', # Text is center justified vertically.
##
##            output]

#https://stackoverflow.com/questions/10725225/ffmpeg-single-quote-in-drawtext
def ffmpeg_command(text, intro, video, output, framerate='30000/1001',
                   fontfile="/Library/Fonts/Trebuchet MS.ttf"):
    return ['/usr/local/Cellar/ffmpeg/3.4.1/bin/ffmpeg',
            '-y', '-nostdin', '-nostats', '-i', intro, '-i', video,
            '-filter_complex', (
                '[0:v]drawtext=enable=between(t\,3\,9):'
                'fontcolor=white:fontfile=%r:'
                'fontsize=36:text=%r:'
                'x=text_w/16:y=(h-text_h)/2[i1];'
                '[0:a][1:a]concat=n=2:v=0:a=1[outa];'
                '[i1][1:v]scale2ref[i2][v2];'
                '[i2][v2]concat=n=2[outv]' % (fontfile, text)),
            '-map', '[outv]', '-map', '[outa]', '-r', framerate,
            '-preset', 'ultrafast',
            output]

def finish(namespace):
    """Finish operation for spaceraid."""
    # Take the video files in the given directory and add the intro to the
    # video, creating the specific intro.
    if not namespace.source_files:
        raise NotImplementedError("Haven't made finish yet.")

    process_files = [] # Files that need to be processed.

    # Set the depth of the walk.
    if namespace.depth != None:
        depth = namespace.depth
    elif namespace.recurse:
        depth = -1
    else:
        depth = 0

    # Walk through all of the given files.
    for f in namespace.source_files:
        # If a file is given, just use that.
        if os.path.isfile(f):
            process_files.append(f)
        # Otherwise, depends on recursive and depth.
        elif os.path.isdir(f):
            for root, dirs, files in walklevel(namespace.source_files, depth):
                process_files.extend(files)

    # Filter through only the files with the tags.
    if namespace.tags == "All":
        # If "All" videos,
        # process_files is filtered_files.
        filtered_files = process_files
    else:
        filtered_files = []
        # Ok, now work of process_files to make this.
        # Depending on "tags", only read some of the videos.
        for f in process_files:
            try:
                tag = xattr.getxattr(f, 'com.apple.metadata:_kMDItemUserTags')
            except OSError:
                # There is no tag com.apple.metadata:_kMDItemUserTags.
                tag = b''
            except IOError:
                # File does not exist. (Using IOError for python2 compatability.)
                logging.error(
                    "File %r did not exist when extended attributes were accessed."%f)
                # Just keep going with other files.
                continue

            # Now, 'tag' still contains a lot of extra data that we need to remove.
            # The effective "tag" is really the word "Red", "Green", or "Yellow",
            # whichever one shows up LAST in the tag.

            # I know this can be done with regex, but it would be more complicated.
            red_index   = tag.rfind(b'Red')
            green_index = tag.rfind(b'Green')
            yellow_index= tag.rfind(b'Yellow')

            index = max(red_index, yellow_index, green_index)

            if index == -1:
                # No tags.
                continue
            elif index == green_index:
                # Use this video.
                filtered_files.append(f)
            elif index == yellow_index and 'Y' == namespace.tags[0]:
                # If the tag is Yellow and so is the preset, use video.
                filtered_files.append(f)
            # Any other situation, don't include video.

    # Now take filtered files and process all of them.
##    import pprint
##    print('#' * 80)
##    pprint(filtered_files)
##    raise NotImplementedError("Haven't made finish yet.")
##
##    command = (# FIRST, full path to ffmpeg.
##        '''/usr/local/Cellar/ffmpeg/3.4.1/bin/ffmpeg '''
##        # Load the 9 second intro.
##        '''-i "Video Intro.mov" '''
##        # Draw the match text, from Intro Font.ttf
##        '''-vf drawtext="fontfile=/Library/Fonts/Trebuchet MS.ttf: text=%r:'''
##        # From 3 to 9 sec, and make color white.
##        '''enable='between(t,3,9)': fontcolor=white: '''
##        # Size, and text position.
##        '''fontsize=36: x=text_w/16: y=(h-text_h)/2" '''
##        # Output file location.
##        '''%r''')
    # Needs text and output location.

    # In order to build the output.
    # 1) Get the video dimensions to create the graphics from the source video.
    #    May need to also get the codec.
    # 2) Build the intro graphic, pipe it to a named stream.
    # 3) Concat the two videos together and write out to disk.

    for f in filtered_files:
        # TO make output file, get basename from f and put it on target_dir
        basename = os.path.basename(f)
        out_file = os.path.join(namespace.target_dir, basename)

        # Also the text in the box is the name of the original video.
        text = basename.rstrip('.mp4').rstrip('.mov')

        command = ffmpeg_command(text, 'Video Intro.mov', f, out_file)

        logging.debug(subprocess.list2cmdline(command))

        process = subprocess.Popen(command, stderr = subprocess.PIPE)

        # Monitor the process as it runs.
        while process.poll() is None:
            x = process.stderr.readline()
            if x:logging.debug("ffmepg:%r" % x.decode(errors='replace').rstrip('\n'))
            time.sleep(.1)
        x = process.stderr.readline()
        if x: logging.debug("ffmepg:%r" % x.decode(errors='replace').rstrip('\n'))

        logging.debug("ffmpeg exited with status %d." % process.poll())

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

parser.add_argument('target_dir',type=PathType(type=('dir','file').__contains__,
                                               dash_ok=True, exists = None),
                    help = "Output folder for processed videos.")

def get_data_log(namespace):
    """Open the data log if it is not already."""
    if isinstance(namespace.data_log, str):
        namespace.data_log = open(namespace.data_log, "a+", buffering = 1)

        namespace.data_log.seek(0)
    return namespace.data_log

def main(args = None):
    results = parser.parse_args(args)

    # -l implementation.
    logging.getLogger().setLevel(results.log_level)
    logging.info("Passed args: %r" % args)

    # Flatten the source_files varible to just be a list of files.
    # Not a concentric list of files.
    results.source_files = sum(results.source_files, [])
    pprint(vars(results))

    try:
        results.operation(results)
    except KeyboardInterrupt:
        logging.info("Keyboard Interrupt")
        parser.exit(130, "Keyboard Interrupt")
    except:
        # Any error, including Keyboard, print something and exit.
        logging.exception(sys.exc_info()[1])

        # Don't give a nice clean exit code. There has been an error, crash.
        raise

if __name__ == '__main__':
    #main(['-v','finish','Results/Saturday 3-11-17_ND/Practice 3 of 78.mp4','.'])
    #main(['-v','parse','/Users/matthewschweiss/Documents/Robotics/spaceRAID/Examples/Saturday 3-11-17_ND.mp4','/Users/matthewschweiss/Documents/Robotics/spaceRAID/'])
    #main(['parse', '-', '-', 'example_folder'])
    main()
