#!/usr/bin/env python
"""Takes the video feed and looks for signs that a match is there."""
import sys
import math
import logging

import video_loader
import process_frames

from collections   import Counter # Counts frequency of
from terminalsize import get_terminal_size

MATCH_LENGTH = 188 # seconds (can be different with weird matches)

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

MOMENT_MINIMUM_FRAMES = 2 # Least number of identical frames needed to believe a result.
MOMENT_MAXIMUM_FRAMES = 5 # Most number of frames needed to use majority vote.
MOMENT_IDENTICAL_PERCENTAGE = 4./5 # Percentage required of identical frames.

def read_moment(video, frame_count = None):
    """Read text at the frame number (frames from start of video).
    If frame_count is less than 0, read from current video position.
    """
    # For different MOMENT_MINUMUM_FRAMES
    # 1: Take next frame.
    # 2: Take 1 previous frame and next 1.
    # 3: Take 1 previous frame and next 2.
    # 4: Take 2 previous frames and next 2.
    # 5: Take 2 previous frames and next 3.
    #...
    frames = [] # The frames that need to be analyized.
    moment = Counter() # List to put the frame results in.

    # Set the video back MOMENT_MINIMUM_FRAMES//2 frames.
    if frame_count < 0:
        frame_count = video.get_frame_index()

    video.set_frame_index(frame_count - MOMENT_MINIMUM_FRAMES // 2)

    # Add the inital frames to the list.
    for num in range(MOMENT_MINIMUM_FRAMES):
        frames.append(video.get_frame())

    # Now process the list.
    for frame in frames:
        if frame is None:
            logging.error("frame is None")
            continue
        name, time = process_frames.read_image(frame)

        # Add another frame if this one failed.
        # But if we have reached max frames, do nothing.
        if (name is None or time is None) and len(frames) < MOMENT_MAXIMUM_FRAMES:
            # Failed frame read.
            frames.append(video.get_frame()) # Read one more frame.

        # Save the results.
        moment[(name, time)] += 1

    # Now take the results and figure out the reading. Lets do some scrying.
    # We are looking for identical items. Are there more than
    # MOMENT_IDENTICAL_PERCENTAGE identical frames?

    try:
        # Most common match.
        common, n = moment.most_common(1)[0] # Returns the most common element.
    except IndexError:
        # moment.most_common is emply?
        logging.debug("No readable frames from video %r." % video.name)
        return None, None # Failed

    # Is the percentage of the most common frame greater than the needed
    # percentage?
    if float(n)/sum(moment.values()) > MOMENT_IDENTICAL_PERCENTAGE:
        # Yes, Success!
        # Return the common than!
        return common
    # Otherwise, this fails.
    return None, None

VERBOSE = 2

def read_video(video):
    """Analyze and find the matches in a video."""
    # Set up the video stream.
    video.set_timestamp(0)

    # Run Moment every 60 seconds.
    timestamp = video.get_timestamp()
    video_length = video.get_frame_count() * video.get_fps()
    blank_count = 0
    while timestamp < video_length:
        video_loader.show_image(video.grab_frame())
        name, time = read_moment(video)
        
        if name is not '' or time is not '':
            # If anything.
            if blank_count:
                print("")
            print("Read timestamp %8.2f to be %r" % (timestamp, (name, time)))
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

        timestamp += MATCH_LENGTH / 3 * 1000 # We want at least two frames per
                                             # match. This means we need three
                                             # chances.

        video.set_timestamp(timestamp)

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    process_frames.init()
    video = video_loader.Video("./Examples/Saturday 3-11-17_ND.mp4")
    try:
        read_video(video)
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        video_loader.close_image()
