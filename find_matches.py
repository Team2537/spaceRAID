"""Takes the video feed and looks for signs that a match is there."""
import math

import video_loader
import process_frames

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
MOMENT_REQUIRED_WIN_MARGIN = 2 # The amount a majority must win by to get a valid result.

def read_moment(video, frame_count):
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

    # Set the video back MOMENT_MINIMUM_FRAMES//2 frames.
    if timestamp < 0:
        frame_count - video.get_frame_count()

    video.set_frame_count(frame_count - MOMENT_MINIMUM_FRAMES // 2)

    for num in range(MOMENT_MIMIMUM_FRAMES):
        frames.append(video.read())

    
    
