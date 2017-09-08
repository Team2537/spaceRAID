#!/usr/bin/env python
"""
A piece of python code to test the effectiveness of "extract_text.py"
to better decode the video.

This loads images that have previously been chopped from the video.
It also uses a list of text with the text in the images manual transcribed by
me.
"""
import re
import os
import sys
import time
import math
import difflib
import logging

# And the local ones.
import video_loader
import process_frames

from collections import OrderedDict, namedtuple
# For the talking to screen
try:
    from dummy_easygui import tkinter_check
except ImportError:
    # No dummy_easygui, just assume easygui works.
    import easygui
else:
    if tkinter_check():
        # Yes, we can use easygui.
        import easygui
    else:
        # Use Dummy Command Line Package.
        import dummy_easygui as easygui
    del tkinter_check # Clean-Up

__author__ = "Matthew Schweiss"
__version__ = "0.5"

__all__ = ["VERBOSE", "TRANSCRIPT_FILE", "main"]

VERBOSE = 7 # EDIT HOW MUCH IS PRINTED

# input, basestring, and long for python 2.X and 3.X
try:
    raw_input
except NameError:
    raw_input = input
try:
    long
except NameError:
    long = int
try:
    basestring
except NameError:
    try:
        basestring = str, unicode
    except NameError:
        basestring = str

# For more consice repr
from repr import repr

LOGGING_LEVEL = None
VIDEO_WINDOW = None

# Make absolute paths.
try:
    __file__
except NameError:
    print_("Finding file location.")
    import inspect
    __file__ = os.path.abspath(
        inspect.getframeinfo(inspect.currentframe()).filename)
    del inspect # Don't pollute namespace.

def average(numbers):
    """Find the average of all of the numbers."""
    return float(sum(numbers)) / len(numbers) # Average

def similar(a, b):
    """Evaluate the similarity of two strings."""
    # This is built into python. Python is Great!!!
    return difflib.SequenceMatcher(None, a, b).ratio()

class Image_Transcript():
    """Read the transcript of what happened in the video."""
    def __init__(self, image_dir, image_format, transcript_file):
        """Create a transcript."""
        # make the file and directory absolute.
        self.source = open(transcript_file)
        self.last_frame = None
        self.next_frame = None

        self.image_dir    = os.path.normpath(image_dir)
        print("Image Directory: %s" % image_dir)
        self.image_format = image_format

    def _parse(self, line):
        """Parse the line into a readable form."""
        logging.info("Read line %r." % line)
        line = line.strip()
        if not line or line[:1] == '#': # Comment, ignore line.
            return None
        content = list(re.split("\\t", line, 3))
        while len(content) < 3:content.append("")
        frame_number, name_result, time_result = content[:3]
        # frame_number is a string, try to parse.
        if not frame_number.isdigit():
            frame_number = os.path.basename(frame_number)
            if frame_number.startswith("image"):
                # File is image\d+\.(?:jpg|png)
                ext_start = frame_number.rfind(".")
                if ext_start:
                    frame_number = frame_number[5:ext_start]
                else:
                    frame_number = frame_number[5:]

        if frame_number.isdigit():
            frame_number = int(frame_number)
        else:
            logging.warning(
                "Could not read the frame_number %r from transcript %r." \
                % (content[0], self.source.name))
            frame_number = self.last_frame[0] + 1 if self.last_frame else 1

        # Now, take the frame_number and actually load the frame.
        file_path = os.path.join(self.image_dir, self.image_format % frame_number)
        frame = video_loader.load_image(file_path)
        # Finished processing, now do something with it.
        return frame_number, frame, name_result, time_result

    def next(self):
        """Return the next frame."""
        rerun = True
        while rerun: # Recursion is needed at least once, maybe more.
            # Stop rerun
            rerun = False

            if self.closed:
                raise StopIteration()
            # If we have a next_frame we are working toward, do that.
            if self.next_frame is not None and self.last_frame is not None:
                if self.last_frame[0] + 1 < self.next_frame[0]:
                    # Next frame is NOT immediately after next frame.
                    # Return the last frame again.
                    self.last_frame[0] += 1
                    return tuple(self.last_frame[1:])# Don't return frame_number
                elif self.last_frame[0] + 1 >= self.next_frame[0]:
                    # We have gone through all of the required frames.
                    # Finish this iteration.
                    self.last_frame = self.next_frame
                    self.next_frame = None
                    return tuple(self.last_frame[1:])# Don't return frame_number

            # Otherwise, load another frame.
            else:
                for line in self.source:
                    # Send the new line to be parsed.
                    line = self._parse(line)
                    if line is None:
                        continue
                    frame_number, frame, name_result, time_result = line

                    if self.last_frame is None or \
                       frame_number == self.last_frame[0] + 1:
                        # This is the next frame, go ahead and return it.
                        self.last_frame=[frame_number,frame,name_result,time_result]

                        self.next_frame = None
                        return tuple(self.last_frame[1:]) # Don't return frame_number.
                    else:
                        # This frame is actually for a frame that has not happened yet.
                        # The current frame is actually the same as the last frame.
                        #self.last_frame = self.next_frame
                        self.next_frame=[frame_number,frame,name_result,time_result]

                        # Rerun to return first frame.
                        rerun = True
                        break
                else:
                    # Finished file. We are done here.
                    self.close()

    __next__ = next

    def __iter__(self):
        """Move through the next frame."""
        while True:
            r = self.next()
            if r is None:
                logging.debug("Image Transcript Read EOF.")
                raise StopIteration()

            else:
                yield r

    @property
    def closed(self):
        """Return if the file is closed."""
        return self.source.closed

    def close(self):
        """Close the file."""
        if not self.closed:
            self.source.close()

    def __enter__(self):
        """Begin use in a "with" statment."""
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the file."""
        self.close()

class Result_Handler():
    """
    A class to collect the readings, store, save, and analyze the data.
    This allows for much more arithmatic to be done but with a less
    clutter in test().
    """
    __all__ = ('CORRECT_FRAME', 'CORRECT_NAME_FRAME', 'CORRECT_TIME_FRAME',
               'FAILED_FRAME', 'add_frame', 'average_name_time', 'average_time',
               'average_time_time', 'percent_partial_name_matches',
               'percent_partial_time_matches', 'total_time')
    
    ENTRY_TYPE      = namedtuple("Entry", ("type","result","real_text"))
    IMAGE_DATA_TYPE = namedtuple("Image_Data", ("number","name","time","duration"))

    # For the filtering.
    not_none = staticmethod(lambda x: x is not None)
    
    def __init__(self, test_function):
        """Create a Result Handler, function is the name of the function used
           in the test.
        """
        #   Dict of the number of each image.
        #   Each image has the following attibutes (in list).
        #       number      -> The frame number of the image.
        #       name        -> Entry or None
        #       time        -> Entry or None
        #       duration    -> Time for the frame to be processed.
        #           Each entry has the following attributes.
        #               type       -> Either "name" or "time".
        #               result     -> The text that was read from the image.
        #               real_text  -> The actual text that goes with this image.
        if not isinstance(test_function, basestring):
            raise TypeError("test_function must be the name of the function being tested. Not %r." % test_function)
        self.test_function = test_function
        self.total_time = None
        self.entries = OrderedDict()

    # DATA COLLECTION

    def add_frame(self, image_number, name_result, name_real_text,
                  time_result, time_real_text, frame_time):
        """Add all of the information of a frame to the handler."""
        # First, make sure image_number is a number.
        if not isinstance(image_number, (int, long)):
            raise TypeError("Image Number must be an integer or a long, not %r."
                            % image_number)

        # Then, make sure frame_time is a number.
        if not isinstance(frame_time, (int, float, long)):
            raise TypeError("Frame Time must be an integer or a long, not %r."
                            % frame_time)
            
        if image_number in self.entries:
            logging.error("Tried to set the frame %d again." % image_number)
            raise ValueError("Frame %d has already been saved." % image_number)

        # else
        self.entries[image_number] = self.IMAGE_DATA_TYPE(
            number = image_number,
            duration = frame_time,
            name=self.ENTRY_TYPE("name", name_result, name_real_text),
            time=self.ENTRY_TYPE("name", time_result, time_real_text)
            )

    # ANALYTICS
    def _get_set(self, key, function):
        """Under the cover get the values and create the average.
           Key is a function that is given an entry and returns the value
           to be averaged. Key can return None values as these are checked for
           and removed."""
        if function is None:
            return list(filter(self.not_none, (key(f) for f in self.entries.values())))
        # else
        return list(filter(
            self.not_none,(key(f) for f in self.entries.values() if function(f))
            ))

    # A list of a few "filters" for the analytics functions
    FAILED_FILTER       = staticmethod(
        lambda x:x.name is None or x.time is None)
    CORRECT_NAME_FILTER = staticmethod(
        lambda x:x.name.result==x.name.real_text!=None)
    CORRECT_TIME_FILTER = staticmethod(
        lambda x:x.time.result==x.time.real_text!=None)
    CORRECT_FILTER      = staticmethod(
        lambda x:CORRECT_NAME_FRAME(x) and CORRECT_TIME_FRAME(x))

    def count_frames(self, function = None):
        """Count the total number of frames that I have data for."""
        # Works so long as no frame is "None", which should not happen.
        # Just in case, using "lambda x:1" instead of "lambda x:x" will fix that.
        if function is None:
            return len(self.entries)
        # else
        return len(self._get_set(lambda x: True, function))

    #-----------------------------------------------------------------
    # Do we need this functions? I think not.
    def count_failed_frames(self):
        """Count the number of frames that failed to return values."""
        return self.count_frames(self.FAILED_FILTER)

    def count_correct_frames(self):
        """Count the number of frames that  were correctly read."""
        return self.count_frames(self.CORRECT_FILTER)
    
    def count_correct_name_frames(self):
        """Count the number of frames that were correct."""
        return self.count_frames(CORRECT_NAME_FILTER)
    
    def count_correct_time_frames(self):
        """Count the number of name frames that were correct."""
        return self.count_frames(CORRECT_TIME_FILTER)
    # I mean, they are all one line redirects.
    #----------------------------------------------------------------
    
    def percent_partial_name_matches(self, function = None):
        """The average simliarity of a name result to its real answer."""
        return 100. * average(self._get_set(
            lambda x: similar(x.name.result, x.name.real_text)
            if x.name.result != None != x.name.real_text else None,
            function))

    def percent_partial_time_matches(self, function = None):
        """The average simliarity of a time result to its real answer."""
        return 100 * average(self._get_set(
            lambda x: similar(x.time.result, x.time.real_text)
            if x.time.result != None != x.time.real_text else None,
            function))

    # total_time is an attribute
    
    def average_time(self, function = None, raise_error = False):
        """The average time for each frame to be processed.
           A filter can be specified to restrict the set the average is taken
           from.
        """
        if raise_error:
            return average(self._get_set(lambda x:x.duration, function))
        # else
        try:
            return average(self._get_set(lambda x:x.duration, function))
        except ZeroDivisionError:
            return None

def test(src, VIDEO_WINDOW = VIDEO_WINDOW, LOGGING_LEVEL = LOGGING_LEVEL):
    """Test the process frames."""
    results = Result_Handler("process_frames.read_frame()")

    if not VERBOSE:
        print("Frame")
    if process_frames.ADAPTIVE_CLASSIFIER:
        print("ADAPTIVE_CLASSIFIER: Enabled")
    else:
        print("ADAPTIVE_CLASSIFIER: Disabled")
    if process_frames.ALLOW_FAILURE:
        print("ALLOW_FAILURE: Enabled")
    else:
        print("ALLOW_FAILURE: Disabled")
    print("VERBOSE: %d" % VERBOSE)
    print("VIDEO_WINDOW: %r" % VIDEO_WINDOW)
    print("LOGGING_LEVEL: %r" % logging.getLevelName(LOGGING_LEVEL))
    print("Working File: %r" % __file__)

    # Initalize the process_frames.
    print("Initalizing process_frames.")
    process_frames.init()

    # Give pooling information.
    print("Using %d name generators." % process_frames.NAME_POOL.qsize())
    print("Using %d time generators." % process_frames.TIME_POOL.qsize())

    failed_frames = 0
    exc_start_time = time.time()

    try:
        for img_num, k in enumerate(src):
            if isinstance(k, (tuple, list)):
                frame, real_name, real_time = k
            else:
                frame, real_name, real_time = k, None, None

            # Video Window
            if VIDEO_WINDOW:
                video_loader.show_image(frame)

            # Back to analysis
            if frame is None:
                logging.error("Frame failed to read.")
                continue

            frame_time_start = time.time() # Start Timing
            
            read_name, read_time = process_frames.read_image(frame)

            frame_time_stop = time.time() # Stop Timing
            
            frame_time = frame_time_stop - frame_time_start
            # Now use all of those breakdowns to come up with one super selection.
            if VERBOSE == 5:
                print("F %d\tActual\tRead" % img_num)
                print("Name:\t%r\t%r" % (real_name, read_name))
                print("Time:\t%r\t%r" % (real_time, read_time))
            elif VERBOSE == 4:
                print("F %d\tName A:%s\tR:%r\tTime A:%s\tR:%s" %
                      (img_num, real_name, read_name, real_time,
                       repr(read_time) if read_time is not None else read_time))
            elif VERBOSE == 3:
                print("F %d\t%r\t%r" % (img_num, read_nume, read_time))
            elif VERBOSE == 2:
                print("Processing frame %d in %.3f seconds." %
                      (img_num, frame_time))
            elif VERBOSE == 1:
                # Print 1,2,3,4,5,6...9,10,20,30,40,...,100,200,300...
                # If this is a multiple of 10, 100, or 1000 correspondingly.
                # log10(0) will crash so 0 is allowed expicitly.
                if img_num == 0 or img_num % (10 ** math.floor(math.log10(img_num))) == 0:
                    print("Processed up to frame %d in %.3f seconds." %
                          (img_num, time.time() - exc_start_time))
            else:
                # Don't Print Anything.
                pass
            # real_name or real_time could be None if the read failed.
            # In this case. If it is None, do similar as if it were "".
            results.add_frame(img_num, read_name, real_name,
                              read_time, real_time, frame_time)

    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        exc_stop_time = time.time()

        exc_time = exc_stop_time - exc_start_time
        print("")
        # Now that we are done, print summary information.

        # Make sure img_num exists.
        try:
            img_num
        except NameError:
            img_num = 0

        print("%s Frames\tPartial Matches\tPerfect Matches" % img_num)

        not_none = lambda x: x is not None
        # Print Name    
        try:
            name_partial_percent = results.percent_partial_name_matches()
            name_perfect_percent = 100. * results.count_frames(
                results.CORRECT_NAME_FILTER) / results.count_frames()
            print("Name\t\t%6.2f%%\t%6.2f%%" %
                  (name_partial_percent, name_perfect_percent))
        except (IndexError,         # Caused by no results
                ZeroDivisionError   # Caused by "None" results.
                ):
            print("Name\t\tN/A\t\tN/A")
        try:
            time_partial_percent = results.percent_partial_time_matches()
            time_perfect_percent = 100. * results.count_frames(
                results.CORRECT_TIME_FILTER) / results.count_frames()
            print("Time\t\t%6.2f%%\t%6.2f%%" %
                  (time_partial_percent, time_perfect_percent))
        except (IndexError,         # Caused by no results
                ZeroDivisionError   # Caused by "None" results.
                ):
            print("Time\t\tN/A\t\tN/A")
        print("Processed Frames: %d" % results.count_frames())
        print("Failed Frames: %d" % results.count_frames(results.FAILED_FILTER))
        if results.count_frames():
            print(" Average Time:\t%.3f seconds" % results.average_time())
        else:
            print(" Average Time:\tN/A seconds")
        results.total_time = exc_time
        print("   Total Time:\t%.3f seconds" % results.total_time)

def main(args = None, VIDEO_WINDOW=VIDEO_WINDOW,LOGGING_LEVEL=LOGGING_LEVEL):
    # Get test Information
    test_num = easygui.indexbox(
        msg="Hello! What do you want to test?",
        choices=("process_frames.read_frame()", "find_matches.read_moment()")
        )

    if   test_num == 0:
        test_func = process_frames.read_image

    elif test_num == 1:
        test_func = find_matches.read_moment

    if test_num is None:
        # Exit
        return

    # Get VIDEO_WINDOW if needed.
    if VIDEO_WINDOW is None:
        VIDEO_WINDOW = easygui.ynbox("Do you want to display the video feed?")

        if VIDEO_WINDOW is None:
            # Exit
            return

    # Get LOGGING_LEVEL if needed.
    if LOGGING_LEVEL is None:
        LOGGING_LEVEL = easygui.indexbox(
            msg="What amount of debug information do you want to see?",
            choices=("DEBUG and more severe (Most Output).",
                     "INFO and more severe.",
                     "WARNING and more severe.",
                     "ERROR and more severe.",
                     "CRITICAL and more severe.",
                     "FATAL (Least Output).")
            )
       
        if   LOGGING_LEVEL == 0: LOGGING_LEVEL = logging.DEBUG
        elif LOGGING_LEVEL == 1: LOGGING_LEVEL = logging.INFO
        elif LOGGING_LEVEL == 2: LOGGING_LEVEL = logging.WARNING
        elif LOGGING_LEVEL == 3: LOGGING_LEVEL = logging.ERROR
        elif LOGGING_LEVEL == 4: LOGGING_LEVEL = logging.CRITICAL
        elif LOGGING_LEVEL == 5: LOGGING_LEVEL = logging.FATAL

    # Allow for more logging information.
    logging.getLogger().setLevel(LOGGING_LEVEL)

    if test_num == 0:
        # process_frames.read_frame() test.
        # images or video.
        test_set = easygui.indexbox(
            msg = "What test set do you want to use?",
            choices = ('Video "Qualification Match 5.mov" with 7995 frames.',
                       'Video "Saturday 3-11-17_ND.mp4" with 1,194,263 frames.',
                       'Set of 7995 png images.',
                       'Set of 56 jpg images.')
            )
    else:
        # find_matches.read_moment()
        # video only.
        test_set = easygui.indexbox(
            msg = "What test set do you want to use?",
            choices = ('Video "Qualification Match 5.mov" with 7995 frames.',
                       'Video "Saturday 3-11-17_ND.mp4" with 1,194,263 frames.',
                       )
            )

    if test_set is None:
        # Exit
        return

    basename = os.path.dirname(os.path.abspath(__file__))

    if   test_set == 0:
        # Qualification Video.
        src = video_loader.Video(
            os.path.join(basename, "./Examples/Qualification Match 5.mov"))

    elif test_set == 1:
        # Saturday huge video.
        src = video_loader.Video(
            os.path.join(basename, "./Examples/Saturday 3-11-17_ND.mp4"))

    elif test_set == 2:
        # "All" Set.
        src = Image_Transcript(
                os.path.join(basename, "./Examples/All"), "image%d.png",
                os.path.join(basename, "./Examples/All/textInImages.txt")
                )

    elif test_set == 3:
        # "Every5" Set.
        src = Image_Transcript(
                os.path.join(basename, "./Examples/Every5Sec"), "image%d.jpg",
                os.path.join(basename, "./Examples/Every5Sec/textInImages.txt")
                )

    else:
        # Error? How did we get here.
        raise RuntimeError("Could not process the test set %r. Bad number." % test_set)

    # So, now we have src.
    # Run it!
    test(src, VIDEO_WINDOW, LOGGING_LEVEL)

if __name__ == '__main__':
    main()
