#!/usr/bin/env python3
"""Takes the video feed and looks for signs that a match is there."""
import os
import csv
import sys
import math
import queue
import logging
import subprocess

from collections  import Counter # Counts frequency
from terminalsize import get_terminal_size

import video_loader
import process_frames

MATCH_PREROLL = 20 + 20 # seconds

MATCH_LENGTH = 188 + 35 + 50 # seconds (can be different with weird matches)

# So, we now have a function that can take an image and read it.
# What we really need is a function that takes a movie and a time.
# This needs to do multiple readings to assure the accuracy.

# Current idea.
# Find the two frames closest to the requested time and read those two.
# Then, if they disagree or a frame failures to read, read the nearest 5
# frames and majority rules.
# If the 5 have a 2 to 3 vote or other more complex situation, give up.
# Also, I need to have some kind of resource pool to allow for accelerated
# reading.

MOMENT_MINIMUM_FRAMES = 5 # Least number of identical frames needed to believe a result.
MOMENT_MAXIMUM_FRAMES = 9 # Most number of frames needed to use majority vote.
MOMENT_IDENTICAL_PERCENTAGE = 4./5 # Percentage required of identical frames.

##class Video_Data():
##    """Handle the evaluation of data as the video is processed.
##       This gives a simple valuation of how to analyze the video,
##       with the results calculated on the fly.
##    """
##    def __init__(self, video):
##        """Create a new Video_Data class."""
##        self.video = video
##
##        self.video_data = {}
##
##        self.processing_queue = queue.PriorityQueue()
##
##        self.worker_threads = []

try:
    next
except NameError:
    def next(iterator):
        for obj in iterator:
            return obj
        return default

# https://stackoverflow.com/questions/89178/
# in-python-what-is-the-fastest-algorithm-for-removing-duplicates-from-a-list-so
def unique(items):
    """Preserve the order and remove all but the first occurance."""
    found = set([])
    keep = []

    for item in items:
        if item not in found:
            found.add(item)
            keep.append(item)

    return keep

def read_moment(video, data_log = None):
    """Read text at the frame number (frames from start of video).

    If data_log is specified, it is a tsv file with data that has aleady been
    processed from this video file. Cache file could also be blank.
    """
    # First validate data_log is it exists.
    if data_log is not None:
        # This should be an object not a path.

        # Try to check if the file is readable.
        try:
            readable = data_log.readable()
        except AttributeError:
            # Python 2, no "readable" attribute.
            logging.debug("File object did not have a 'readable()' attribute.\n"
                          "Normal for python 2.")

            try:
                data_log.read(0) # Try to read nothing, errors if can't read.
            except IOError:
                readable = False
            else: # Successfully read.
                readable = True

        # Try to check if the file is writable.
        try:
            writable = data_log.writable()
        except AttributeError:
            # Python 2, no "writable" attribute.
            logging.debug("File object did not have a 'writable()' attribute.\n"
                          "Normal for python 2.")

            try:
                data_log.write("") # Try to write nothing, errors if can't write.
            except IOError:
                writable = False
            else: # Successfully wrote.
                writable = True
    else:
        # There is no data_log.
        readable = writable = None

    # For different MOMENT_MINUMUM_FRAMES
    # 1: Take next frame.
    # 2: Take 1 previous frame and next 1.
    # 3: Take 1 previous frame and next 2.
    # 4: Take 2 previous frames and next 2.
    # 5: Take 2 previous frames and next 3.
    #...
    moment = Counter() # Counter to put the frame results in.

    # Set the video back MOMENT_MINIMUM_FRAMES // 2 frames.
    frame_count = video.get_frame_index()

    video.set_frame_index(frame_count - MOMENT_MINIMUM_FRAMES // 2)

    # The frames that need to be analyized.
    frames = [video.get_frame() for num in range(MOMENT_MINIMUM_FRAMES)]

    # Add the inital frames to the list.
    for num in range(MOMENT_MINIMUM_FRAMES):
        frames.append(video.get_frame())

    if readable:
        cache_reader = csv.reader(data_log)

    if writable:
        cache_writer = csv.writer(data_log)

    # Now process the list.
    for frame in frames:
        if frame is None:
            logging.error("frame is None")
            continue

        # First, if there are cached results, use those.
        if readable:
            result = next(cache_reader, None)
            if result is not None:
                frame_index, match_type, match_number, total_matches, time = result

                name = process_frames.Name_Result(match_type, match_number, total_matches)

                if int(frame_index) != frame_count:
                    logging.error("Data file sync failed with current readings.")
                    readable = False # Readings did not match.
                    writable = False # Don't write to a file that can't be synced.
            else:
                readable = None # Depleted, nothing else to read.

        if not readable:
            # Specifically written so if readable fails, this will catch.
            name, time = process_frames.read_image(frame)

            match_type = name.match_type
            match_number = name.match_number
            total_matches = name.total_matches

            # Now save to file if possible.
            if writable:
                cache_writer.writerow((int(frame_count),
                                       match_type,
                                       match_number,
                                       total_matches,
                                       time))

        # Add another frame if this one failed.
        # But if we have reached max frames, do nothing.
        if (not name or not time) and len(frames) < MOMENT_MAXIMUM_FRAMES:
            # Failed frame read.
            frames.append(video.get_frame()) # Read one more frame.

        # Save the results.
        moment[(name, time)] += 1

        # Increment the frame_count
        frame_count += 1

    # Now take the results and figure out the reading. Lets do some scrying.
    # We are looking for identical items. Are there more than
    # MOMENT_IDENTICAL_PERCENTAGE identical frames?

    try:
        # Most common match.
        common, n = moment.most_common(1)[0] # Returns the most common element.
    except IndexError:
        # moment.most_common is empty?
        logging.debug("No readable frames from video %r." % video.name)
        return process_frames.Name_Result('', None, None), None # Failed

    # Is the percentage of the most common frame greater than the needed
    # percentage?
    if float(n)/sum(moment.values()) > MOMENT_IDENTICAL_PERCENTAGE:
        # Yes, Success!
        # Return the common than!
        return common
    # Otherwise, this fails.
    return process_frames.Name_Result('', None, None), None

VERBOSE = 2
SHOW_VISUAL = True

def scan_video(video, data_log = None):
    """Complete an inital scan of the video, trying to find all matches."""
    # Set up the video stream.
    video.set_timestamp(0)

    # Run Moment every 60 seconds.
    timestamp = video.get_timestamp()
    video_length = video.get_frame_count() * video.get_fps()
    blank_count = 0

    # Memory Structure
    match_data = {}
    try:
        while timestamp < video_length:
            if SHOW_VISUAL:
                video_loader.show_image(video.grab_frame())
            name, time = read_moment(video, data_log)
            match_data[timestamp] = name, time
            if name is not '' or time is not '':
                # If anything.
                if blank_count:
                    print("")
                print("Read timestamp %8.2f to be %s, %s"%(timestamp,name,time))
                blank_count = 0
            else:
                blank_count += 1
                if VERBOSE == 1:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                elif VERBOSE == 2:
                    terminal_width = get_terminal_size()[0]
                    if blank_count > terminal_width:
                        # Bar would be longer than the terminal.
                        # Print newline, scrollback counter and continue!
                        print("")
                        blank_count -= terminal_width

                    sys.stdout.write('.' * blank_count + "\r")
                    sys.stdout.flush()

            timestamp += MATCH_LENGTH / 7 * 1000 # We want at least two frames per
                                                 # match. This means we need three
                                                 # chances.

            video.set_timestamp(timestamp)
    finally:
        if blank_count:
            print("")
##            blank_count = 0 # This is not needed. Never checked again.

    # Print some data about what was returned.
    print("Found %d matches." % len(match_data))

    # Now, go through the names and homogenized the total number of matches.

    # Get the frequency of total_matches.
    total_matches=Counter(name.total_matches for name, t in match_data.values())# if name is not None)
    # Remove "None"
    del total_matches[None]

    # Get the most common.
    common_total = total_matches.most_common(1)

    if not common_total:
        print("No Common Totals")
    else:
        common_total, n = common_total[0]

    # Now substitute THAT, for each total_matches.
    for name, time in match_data.values():
##        if name is not None:
##            name.total_matches = common_total
##        else:
##            print("Encountered a None in match_data.")
        name.total_matches = common_total

    return match_data

def time_video(results):
    """Take the dictionary built from video scanner and use it to
       find holes. Returns a list of missing matches, a calculated
       number of list of matches.
    """
    final_times = []
    # First, get a list of all found matches.
    match_names = unique(match[0] for match in results.values())

    # Then for each one, guess the start timestamp, and the end timestamp.
    for match_name in match_names:
        if not match_name:
            continue

        matches = [(timestamp, name, time)
                   for timestamp, (name, time) in results.items()
                   if name == match_name and time]

        if not matches:
            print("Match %s had no usable frames." % match_name)
            continue

        # Alright, for each of these matches, find an average slope between each
        # frame.
        start_time = sum(timestamp / 1000. - int(time)
                         for timestamp, name, time in matches) \
                         / len(matches) - MATCH_PREROLL

        stop_time = start_time + MATCH_PREROLL + MATCH_LENGTH

        final_times.append((match_name, start_time, stop_time))

        print("% 24s starts at % 8d and finishes at % 8d." %
              (match_name, start_time, stop_time))

    return final_times

import time

# ffmpeg -i source-file.foo -ss 1200 -t 600 third-10-min.m4v
# ffmpeg_command = 'ffmpeg -i %r -ss %r -t %r %r'
def ffmpeg_command(source, start_time, stop_time, output):
    return ['ffmpeg',
##              # This line appears to break everything.
            '-loglevel', 'warning', # Less output
            '-ss', str(start_time),
            '-i', source,
            '-t', str(stop_time - start_time),
            '-codec', 'copy', # Don't re-encode, keep the same encoding. Fast

            output]

def write_files(video, timings):
    """Write the videos that are found in the output."""
    # First, get rid of any recongnizable extension.
    video_name = video.name
    if   video_name.endswith(".mp4"): video_name = video_name.rstrip(".mp4")
    elif video_name.endswith(".mov"): video_name = video_name.rstrip(".mov")

    # Create Output Folder.
    output_folder = os.path.join("./Results/", video_name)
    if not os.path.exists(output_folder):
        os.mkdir(output_folder)

    for match_name, start_time, stop_time in timings:
        # Put together the file location.
        output_file = os.path.join(output_folder, str(match_name) + ".mp4")

        if os.path.exists(output_file):
            continue
        print("Make file %s" % output_file)

        # Create and processing command and launch!
        command = ffmpeg_command(video.path, start_time, stop_time, output_file)
        print("Command: %s" % subprocess.list2cmdline(command))
        output=subprocess.Popen(command,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)

        # Monitor the process as it runs.
        while output.poll() is None:
            output.stdout.flush()
            x = output.stdout.readline()
            if x: logging.debug("ffmepg %r" % x)
            time.sleep(.1)
        print("Finished with status %s" % output.poll())

def test(args = None):
    # Get argument.
    if args is None:
        args = sys.argv[1:]

    global video, results, timings
    logging.getLogger().setLevel(logging.DEBUG)
    process_frames.init()
    logging.info("Passed args: %r" % args)
    for f in args:
        if f is None:
            continue
        f = os.path.abspath(f)
        if not os.path.isfile(f):
            logging.error("File %r does not exists." % f)

        video = video_loader.Video(f)
        try:
            results = scan_video(video)
            # Close the windows.
            process_frames.deinit()
            timings = time_video(results)
            write_files(video, timings)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
        finally:
            video_loader.close_image()

if __name__ == '__main__':
    test()
