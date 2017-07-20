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

__author__ = "Matthew Schweiss"
__version__ = "0.5"

__all__ = ["VERBOSE", "TRANSCRIPT_FILE", "main"]

VERBOSE = 4 # EDIT HOW MUCH IS PRINTED
IMAGE_FORM      = "image%d.png"                     or "image%d.jpg"
IMAGE_FOLDER    = "./Examples/All"                  or "./Examples/Every5Sec"
TRANSCRIPT_FILE = "./Examples/All/textInImages.txt" or "./Examples/Every5Sec/textInImages.txt"

# Make absolute paths.
try:
    __file__
except NameError:
    print_("Finding file location.")
    import inspect
    __file__ = os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename)
    del inspect # Don't pollute namespace.

basename = os.path.dirname(__file__)
IMAGE_FOLDER    = os.path.abspath(os.path.join(basename, IMAGE_FOLDER))
TRANSCRIPT_FILE = os.path.abspath(os.path.join(basename, TRANSCRIPT_FILE))

def average(numbers):
    """Find the average of all of the numbers."""
    return sum(numbers) * 1. / len(numbers) # Average

def similar(a, b):
    """Evaluate the similarity of two strings."""
    # This is built into python. Python is Great!!!
    return difflib.SequenceMatcher(None, a, b).ratio()

class Transcript():
    """Read the transcript of what happened in the video."""
    def __init__(self, file):
        """Create a transcript."""
        self.source = open(file)
        self.last_frame = None
        self.next_frame = None

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
        # Finished processing, now do something with it.
        return frame_number, name_result, time_result

    def __iter__(self):
        while not self.source.closed:
            # If we have a next_frame we are working toward, do that.
            if self.next_frame is not None and self.last_frame is not None:
                if self.last_frame[0] +1 < self.next_frame[0]:
                    # Next frame is NOT immediately after next frame.
                    # Return the last frame again.
                    self.last_frame[0] += 1
                    yield self.last_frame
                elif self.last_frame[0] + 1 >= self.next_frame[0]:
                    # We have gone through all of the required frames.
                    # Finish this iteration.
                    self.last_frame = self.next_frame
                    self.next_frame = None
                    yield self.last_frame

            # Otherwise, load another frame.
            else:
                for line in self.source:
                    # Send the new line to be parsed.
                    line = self._parse(line)
                    if line is None:
                        continue
                    frame_number, name_result, time_result = line

                    if self.last_frame is None or \
                       frame_number == self.last_frame[0] + 1:
                        # This is the next frame, go ahead and return it.
                        self.last_frame = [frame_number, name_result, time_result]
                        yield self.last_frame
                        self.next_frame = None
                        break
                    else:
                        # This frame is actually for a frame that has not happened yet.
                        # The current frame is actually the same as the last frame.
                        #self.last_frame = self.next_frame
                        self.next_frame = [frame_number, name_result, time_result]
                        break
                else:
                    # Finished file. We are done here.
                    self.close()
                    break

    def close(self):
        if not self.source.closed:
            self.source.close()
                
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

def main():
    """Test the process frames."""
    

    
    global read_name_results, read_time_results
    # Just to get everything on one line, here are some convinent functions.
    read_name_results = []
    read_time_results = []
    
    exc_time_results  = []

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

    failed_frames = 0
    exc_start_time = time.time()

    try:
        for img_num, real_name, real_time in Transcript(TRANSCRIPT_FILE):
            img_file = os.path.join(IMAGE_FOLDER, IMAGE_FORM % img_num)
            img_file = os.path.abspath(img_file)
            
            frame_time_start = time.time() # Timing

            # Actually call the function.
            frame = video_loader.load_image(img_file)
            if frame is None:
                logging.error("Frame %r was not present." % img_file)
                continue
            read_name, read_time = process_frames.read_image(frame)

            frame_time_stop = time.time() # Timing
            frame_time = frame_time_stop - frame_time_start
            # Now use all of those breakdowns to come up with one super selection.
            if VERBOSE == 5:
                print("F %d\tActual\tRead" % img_num)
                print("Name:\t%r\t%r" % (real_name, read_name))
                print("Time:\t%r\t%r" % (real_time, read_time))
            elif VERBOSE == 4:
                print("F %d\tName A:%s\tR:%r\tTime A:%s\tR:%r" %
                      (img_num, real_name, read_name, real_time, read_time))
            elif VERBOSE == 3:
                print("F %d\t%r\t%r" % (img_num, read_nume, read_time))
            elif VERBOSE == 2:
                print("Processing frame %d in %.3f seconds." %
                      (img_num, frame_time))
            elif VERBOSE == 1:
                # Print 1,2,3,4,5,6...9,10,20,30,40,...,100,200,300...
                # If this is a multiple of 10, 100, or 1000 corrospundingly.
                # log10(0) will crash so 0 is allowed expicitly.
                if img_num == 0 or img_num % (10 ** math.floor(math.log10(img_num))) == 0:
                    print("Processed up to frame %d in %.3f seconds." %
                          (img_num, time.time() - exc_start_time))
            else:
                # Don't Print Anything.
                pass
            # real_name or real_time could be None if the read failed.
            # In this case. If it is None, do similar as if it were "".
            read_name_results.append(
                (read_name, similar(real_name, read_name or ""), read_name == real_name))

            read_time_results.append(
                (read_time, similar(real_time, read_time or ""), read_time == real_time))

            if read_name is None or read_time is None:
                failed_frames += 1
            exc_time_results.append(frame_time)

    except KeyboardInterrupt:
        print("KeyboardInterrupt")
    finally:
        exc_stop_time = time.time()

        exc_time = exc_stop_time - exc_start_time
        print("")
        # Now that we are done, print summary information.
        print("%s Frames\tPartial Matches\tPerfect Matches" % img_num)
        if read_name_results:
            name_partial_percent = average(zip(*read_name_results)[1]) * 100
            name_perfect_percent = average(zip(*read_name_results)[2]) * 100
            print("Name\t\t%6.2f%%\t%6.2f%%" %
                  (name_partial_percent, name_perfect_percent))
        else:
            print("Name\t\tN/A\tN/A")
        if read_time_results:
            time_partial_percent = average(zip(*read_time_results)[1]) * 100
            time_perfect_percent = average(zip(*read_time_results)[2]) * 100
            print("Time\t\t%6.2f%%\t%6.2f%%" %
                  (time_partial_percent, time_perfect_percent))
        else:
            print("Time\t\tN/A\tN/A")
        print("Processed Frames: %d" % len(exc_time_results))
        print("Failed Frames: %d" % failed_frames)
        if exc_time_results:
            print(" Average Time:\t%.3f seconds" % average(exc_time_results))
        else:
            print(" Average Time:\tN/A seconds")
        print("   Total Time:\t%.3f seconds" % exc_time)

if __name__ == '__main__':
    main()
