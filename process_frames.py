#!/usr/bin/env python
"""
Take a frame and do the reading of it.

read_image(img)     Read the image with the ocr.

TODO
Add logging with all results going to info() and all failures going to debug().
Add a threading pool so x images can be processed by y threads.
Make the threading pool smart so to increase efficiency on the fly.
Figure out how ocr.ClearAdaptiveClassifier() works so I can actually use it
efficiently.
"""
import re
import os
import cv2
import sys
import difflib
import logging # I will get to adding this eventually.
from math import ceil, floor # For pixel corrections.
from collections import namedtuple

import tesserocr
from PIL import Image
from numpy import ndarray
from extract_lib import extract_image
# Format: (x, y, width, height) Assumed frame size (512, 288)

# These are the new pixel values.
# Here are the results from some testing on the detection rects.
# The format is (Green:Yellow:Red)/Total 0.0%.
# Green         - A good video with match and end score board.
# Yellow        - An ok video lacking part of the match or the score board.
#                 Possible mislabeled total matches. The role of thumb is the
#                 match should be in progress or starting at least halfway
#                 through the clip.
# Red           - A bad video either lacking the match or mislabeled.
# Total         - Total number of found matches. Note that "Test Match" will
#                 show up here but not as green, yellow, or red.
#
# New Name: MATCH_NAME_RECT = ( 90, 224, 130,  16)
# New Time: MATCH_TIME_RECT = (244, 240,  28,  16)
#
# Old Name: MATCH_NAME_RECT = (107, 224, 103,  16)
# Old Time: MATCH_TIME_RECT = (244, 243,  28,  13)
# Test Video 1 (Friday 4-7-17_ND)
# (New Name And Time)		(21:11:12)/44	47.73%
# (Old Name And Time)		(29:10:20)/60	48.33%
# (New Name, Old Time)		(25:10:18)/54	46.30%
#
# So evidently, the "new" settings are not so great.

# That is why both settings are here.
# The NEW settings.
##MATCH_NAME_RECT = ( 90, 224, 130,  16)
##MATCH_TIME_RECT = (244, 240,  28,  16)

# The OLD settings.
MATCH_NAME_RECT = (107, 224, 103,  16)
MATCH_TIME_RECT = (244, 243,  28,  13)

DEFAULT_SIZE = (512, 288)

# And for threading
import threading
try:
    import Queue as queue
except ImportError:
    import queue

MATCH_LENGTH = 180

__all__ = ["read_image", "ALLOW_FAILURE", "VERBOSE", "REG_NAME_ENLARGE",
           "REG_TIME_ENLARGE", "EXT_TIME_ENLARGE", "ADAPTIVE_CLASSIFIER"]

__author__ = "Matthew Schweiss"
__version__ = "1"

REG_NAME_ENLARGE = 5
REG_TIME_ENLARGE = 20
EXT_TIME_ENLARGE = 14

DEBUG = True
ADAPTIVE_CLASSIFIER = True
ALLOW_FAILURE = True

# Basically, try to convert everything to one of these formats.
NAME_FORMATS = {
    ""                          :   "",
    "Test Match"                :   't1',
    "Qualification # of #"      :   'q2',
    "Quarterfinal # of #"       :   'qf3',
    "QuarterFinal Tiebreaker #" :   'qft4',
    "Semifinal #"               :   'sfn5',
    "Semifinal # of #"          :   'sf6',
    "SemiFinal Tiebreaker #"    :   'sft7',
    "Final #"                   :   'f8',
    "Practice # of #"           :   'p9',
    }

NAME_CHAR_LIST = "".join(sorted(set("".join(NAME_FORMATS)).difference("#")))

NUMBER_CORRECTIONS = {
    # This is a list of non-number letters and numbers that are
    # sometimes accidently encoded as them.
    "s" : "5",
    "S" : "5",
    "1a": "78", # Evidently a mistake the system will make
    "00": "80",
    "lo": "80",
    "l0": "80",
    "no": "80",
    }

def is_numpy_image(image):
    """Check that the image is a numpy image, or really an array of pixels."""
    return isinstance(image, ndarray)

def similar(a, b):
    """Evaluate the similarity of two strings."""
    # This is built into python. Python is Great!!!
    return difflib.SequenceMatcher(None, a, b).ratio()

def enlarge(image, ratio, interpolation = None):
    """Take the image and increase the size by ratio."""
    # INTER_LINEAR is the default setting.
    # Valid settings are:
    # cv2.INTER_NEAREST - a nearest-neighbor interpolation
    # cv2.INTER_LINEAR - a bilinear interpolation (used by default)
    # cv2.INTER_AREA - resampling using pixel area relation. It may be a
    #                  preferred method for image decimation, as it gives
    #                  moire'-free results. But when the image is zoomed, it
    #                  is similar to the INTER_NEAREST method.
    # cv2.INTER_CUBIC - a bicubic interpolation over 4x4 pixel neighborhood
    # cv2.INTER_LANCZOS4 - a Lanczos interpolation over 8x8 pixel neighborhood
    if interpolation is None:
        return cv2.resize(src = image, dsize = (0,0), fx = ratio, fy = ratio)
    # else
    return cv2.resize(src = image, dsize = (0,0), fx = ratio, fy = ratio,
                      interpolation = interpolation)

def name_reader():
    """Read all of the images as they get introduced to the generater."""
    # First, build the character list.
    # The only characters that should be in this are 0-9 and any character in
    # the NAME_FORMATS.
##    char_list = set(''.join(NAME_FORMATS))
##    char_list.remove("#") # It is in the NAME_FORMATS but has special meaning.
##    # Because the list needs to be a string, convert it.
##    # Don't forget the numbers. We need those.
##    char_list = char_list.union("0123456789")
##    char_list = ''.join(sorted(char_list))
    # For test, trying a static list that intentially does not have all
    # letters.
    char_list = " 0123456789MPQTacefhilmnopqrstuy"

    image = yield None
    # Call the tesseract library and build the processing object ("ocr").
    # Specify that all text should be in a single line (SINGLE_LINE).
    with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.SINGLE_LINE) as ocr:
        # Set the character list.
        ocr.SetVariable("tessedit_char_whitelist", char_list)
        while True: # Process all of the imates as they are passed by .send()
            ocr.SetImage(image)
            match_name = ocr.GetUTF8Text()
            # Previously, confidence was also returned. However, it is not useful.
            image = yield match_name
            if ADAPTIVE_CLASSIFIER:
                ocr.ClearAdaptiveClassifier()
            # Turns out this optimization does help but this name processing
            # actually is slightly hurt. Keep it anyway, it seems to be not that
            # bad.

def time_reader():
    """Read all of the images as they get introduced to the generater."""
    image = yield None

    # Call the tesseract library and build the processing object ("ocr").
    # Specify that all text should be in a single chunk (SINGLE_WORD).
    with tesserocr.PyTessBaseAPI(psm=tesserocr.PSM.SINGLE_WORD) as ocr:
        # We are looking for time. This means we are looking for numbers.
        ocr.SetVariable("tessedit_char_whitelist", "0123456789")
        while True:
            ocr.SetImage(image) # Set the image.
            match_time = ocr.GetUTF8Text() # Get the result (takes a bit)
            image = yield match_time # Return and get new image.
            if ADAPTIVE_CLASSIFIER:
                ocr.ClearAdaptiveClassifier()
            # Turns out this optimization does help time readings a lot!
            # From a 68.73% perfect read to a 75.45%!

class Name_Result(object):
    """Name_Result(match_type, match_number, total_matches)"""
    # Match Abbrevation which is the reverse of NAME_FORMATS.
    MATCH_ABBR_FORMATS = dict((item, key) for key, item in NAME_FORMATS.items())

    # Using __slots__ and __new__ to speed this up a little.
    __slots__ = ('match_type', 'match_number', 'total_matches')

    def __new__(cls, match_type, match_number, total_matches):
        """Create new instance of Name_Results(match_type, match_number, total_matches)"""
        self                = object.__new__(cls)
        # See if the match_type is a match name, or an abbreviation.
        if match_type in self.MATCH_ABBR_FORMATS:
            self.match_type = match_type
        elif match_type in NAME_FORMATS:
            self.match_type = NAME_FORMATS[match_type]
        else:
            raise ValueError("match_type is not in NAME_FORMATS.")
        # Now the other varibles: match_number, total_matches, and match time.
        # None, is allowed for all values.
        self.match_number   = int(match_number) if match_number is not None else None
        self.total_matches  = int(total_matches)if total_matches is not None else None
        return self

    def __bool__(self):
        """If this is object exists."""
        # There is no type, False.
        if self.match_type is "":
            return False
        # If there is no match_number, and one is needed, False.
        if self.match_type.count("#") >= 1 and self.match_number is None:
            return False

        # Otherwise true.
        return True

    __nonzero__ = __bool__

    def __str__(self):
        """Print string representation of the object."""
        if not self:
            return "None"
        match_name = self.MATCH_ABBR_FORMATS[self.match_type]
        # Add Match Number
        if "#" in match_name and self.match_number != None:
            match_name = match_name.replace("#", str(self.match_number), 1)
        # Add Match Quantity
        if "#" in match_name and self.total_matches != None:
            match_name = match_name.replace("#", str(self.total_matches), 1)
        return match_name

    def __repr__(self):
       """Return a nicely formatted representation string"""
       return('Name_Result(match_type=%r, match_number=%r, total_matches=%r)'
              % (self.match_type, self.match_number, self.total_matches))

    def __eq__(self, obj):
        """Compare this object to other obj."""
        # First check, that this has the varibles.
        return str(self) == str(obj)

    # Now, the comparative operators.
    def __cmp__(self, obj):
        """Compare this objoect to anouther."""
        # -1 for less, 0 for equal, 1 for greater
        if self.__eq__(obj):
            return 0 # Yaaaay, Equal
        # I am less, if I am an earlier match type.

        try:
            # First, check if the match_types match.
            # If so, check the match number.
            if self.match_type == obj.match_type:
                # Now, check the match number.
                return cmp(self.match_number, obj.match_number)

            # Match type order is marked by the last character in the abbreviation.
            # Except for "" which is still blank and goes first.

            if self.match_type == "":
                # Now, we already know self.match_type != obj.match_type
                # There for I know obj.match_type is not ""
                # I must be less.
                return -1

            # Otherwise, check the number of our type.
            return cmp(int(self.match_type[-1]), int(obj.match_type[-1]))
        except AttributeError:
            # obj did not have some attribute.
            raise TypeError("obj for cmp was of type %s, not Name_Result." %
                            type(obj))

#https://stackoverflow.com/questions/390250/elegant-ways-to-support-equivalence-equality-in-python-classes
    def __hash__(self):
        """Override the default hash behavior (that returns the id or the object)"""
        return hash((self.__class__, str(self)))

##def smart_read_name(name_text):
##    """Post Process the name text."""
##    # Make name, special.
##    #name = Reading_Result.from_name(name)
##    # First clean reg_name a little bit.
##    name_text = name_text.strip()
##    match_name = re.sub("\\s+", " ", name_text)
##
##    # Take the reg_name, put # in for numbers for compare.
##    reg_name_template, n = re.subn("\\d+", "#", match_name)
##
##    match = difflib.get_close_matches(reg_name_template, NAME_FORMATS,
##                                      n = 1, # At most only one result.
####                                      cutoff =.4
####                                      #Particularly Practice needs this.
##                                      )
##    del reg_name_template
##    if not match:
##        return "" # We are done here.
##    else:
##        match = match[0]
##    # So, we have our closest possibility, and our raw input.
##    # Try to extract the numbers.
##    if n == match.count("#"):
##        # We are good, the each number present has a place. Pull them out
##        # and shove them into the other.
##        for num in re.findall("\\d+", match_name):
##            match = match.replace("#", num, 1)
##        return match
##    else:
##        # Well, the numbers don't match?
##        # Well, more reliable than the numbers, is the spacings.
##        raw_words = name_text.split(" ")
##        known_words = list(match.split(" "))
##        if len(raw_words) != len(known_words):
##            # Ok, wrong number of numbers AND words.
##            # Not parseable.
##            if ALLOW_FAILURE:
##                return None
##            else:
##                return name_text
##        else:
##            # The pieces line up. To continue find the "#" pieces and try
##            # to make smart substitutions.
##            for i in range(len(known_words)):
##                if known_words[i] == "#":
##                    raw_word = raw_words[i]
##                    if raw_word.isdigit():
##                        # This is not the problem. Assert this as normal.
##                        known_words[i] = raw_word
##                    else:
##                        # Substitute the number, after working on it.
##                        sub = NUMBER_CORRECTIONS.get(raw_words[i], None)
##                        if sub is None:
##                            # Ok, no idea of what to substitute.
##                            # I am done!
##                            if ALLOW_FAILURE:
##                                return None
##                            else:
##                                return name_text
##                        else:
##                            known_words[i] = sub
##                # Otherwise skip and keep going.
##            # Now return known_words because that is our best option.
##            return ' '.join(known_words)
##        return match_name
#*******************************************************************************

def fix_number(number_text):
    """Get number from fix list and check if this is a logical number."""
    # Correct num1, and make int
    if number_text in NUMBER_CORRECTIONS:
        return int(NUMBER_CORRECTIONS[number_text])
    
    #else, look for numbers that are valid, but not logical.
    if not number_text or len(number_text) > 3 or not number_text.isdigit():
        # Either 0 characters or greater than 3 characters (>1000)
        # Or this is simply not a number.
        return None

    if number_text[0] == "0" and number_text != "0":
        # Preleading '0'
        # Not valid.
        return None

    # else, return the integer represntation, is it exists.
    return int(number_text)

def smart_read_name(name_text):
    """Post Process the name text."""
    # Make name, special.

    # First clean name_text a little bit.
    name_text = name_text.strip() # Remove whitespaces on each end.
    name_text = re.sub(r"\s+", " ", name_text) # Make all spaces one space.

    # Take the name_text, put # in for numbers for comparison.
    name_text_comparable = re.sub(r"\b\d+\b", "#", name_text)

    # Use difflib to figure out the closest match.

    # Cutoff is lowered by .01, this seems to make a difference for something
    # like 'artufinal Tinehmher\n\n' -> QuarterFinal Tiebreaker None
    # while this does not match regularly.

    # Maybe want to lower cutoff even further.
    name_text_template = difflib.get_close_matches(
        name_text_comparable, NAME_FORMATS, n = 1, cutoff = .59)

    # Now, if there is no match, then we are done.
    if not name_text_template or not name_text_template[0]:
        return Name_Result("", None, None) # We are done here.

    # Otherwise, get the match.
    else:
        name_text_template = name_text_template[0]

    # So, we have our closest template, and our input.
    # Try to extract the numbers.
    # Now, the numbers should not have leading '0's.
    # (Though that is allowed for the comparable creation as there should never
    #  be a '0' in the templates.)
    numbers = re.findall(r"\b\d+\b", name_text)
    # Either there is 1 number (match number) or 2 (match number and total matches).
    # Otherwise, make it up!
    # If there is only 1 number needed, take the first. If two are needed
    # then take the first and last.
    # If any number has a leading 0, just call it None.

    correct_number_count = name_text_template.count("#")

    # First, up if we have a lack of numbers, make some up!
    # If there are not NUMBER_CORRECTIONS, skip this step.
    if len(numbers) < correct_number_count and NUMBER_CORRECTIONS:
        # Try again, but this time with a harsher algorthm.
        # Find EITHER, a number or one of the known correctable objects.
        numbers=re.findall(r"\d+|\b"+r"\b|\b".join(NUMBER_CORRECTIONS)+r"\b",name_text)

    # Now, if there are still not any numbers, then the result is just the template.
    if not numbers or not correct_number_count:
        return Name_Result(name_text_template, None, None)

    # Look over the numbers. If they start with "0"s, make them None.
    # If they are legit numbers, make them ints.
    # Actually, we only care about the first and possibly last number.
    if min(correct_number_count, len(numbers)) == 1:
        # Only need one number!
        number = fix_number(numbers[0])
        
        return Name_Result(name_text_template, number, None)

    # Otherwise, two numbers.
    if correct_number_count == 2:
        # Only need first and last number!
        # Do to the last test, we know there are at least two numbers.
        num1, num2 = numbers[0], numbers[-1]

        # Correct num1, and make int
        num1 = fix_number(num1)
        
        # Correct num2, and make int
        num2 = fix_number(num2)

        # num1 should be less than num2, otherwise num2 is wrong.
        if num1 > num2:
            num2 = None

        return Name_Result(name_text_template, num1, num2)

    # If we still don't have a solution, error.
    raise RuntimeError(
        "smart_read_name(%r) found more than two numbers in a template (%r). "
        "This is not valid." % (name_text, name_text_template))
#*******************************************************************************

def smart_read_time(reg_time, ext_time):
    """Tead the time smartly. Post-Processing."""
    # First, remove spaces to make sure everything is good.
    reg_time, ext_time = reg_time.strip(), ext_time.strip()
    # If the extracted value is blank then this is blank unless
    # regular time is at least 3 characters.
    if not ext_time and len(reg_time) <= 2:
        # No text found. Probably no text at all.
        return ""
    # Now, also. If extracted value has a number but regular time is blank,
    # Use the extracted value.

    # A common mistake the match makes is confusing "0" with "1" or "4".
    # Ext_time does not have this problem but can get it wrong.
    if not reg_time or (ext_time == "0" and len(reg_time) == 1):
        time = ext_time
    else:
        time = reg_time

    # Do some simple processing.
    time = time.strip()

    # Sometimes a "1" is appended to the end of a long time.
    # Remove it to improve reliability.
    if len(time) == 4 and time[-1] == "1":
        time = time[:3]

    # Sometimes a "0" is added to the beginning of the text.
    # Remove it to improve reliability.
    # This does require some testing.
    if len(time) > 1 and time[0] == "0":
        time = time[1:]

    # Finished processing.

    # See if this is a valid string and return.
    # Make sure the time is a number and is a decent length.
    if time.isdigit() and int(time) < MATCH_LENGTH:
        return time

    elif ALLOW_FAILURE:
        return None
    else:
        return ""

# Now threading.
# For threading, I need to make a pool of workers to process frames and pass
# them back to the correct functions.
NAME_POOL_SIZE = 2
TIME_POOL_SIZE = 2

NAME_POOL = queue.Queue(NAME_POOL_SIZE)
TIME_POOL = queue.Queue(TIME_POOL_SIZE)

def init():
    """Add the generaters to NAME_POOL and TIME_POOL for processing.
       This can take a little bit of time.
    """
    # Set NAME_POOL to have NAME_POOL_SIZE generators. Because of multithreading,
    # this can fail in many strange ways.
    # Then set TIME_POOL to have TIME_POOL_SIZE generators.
    try:
        for i in range(NAME_POOL_SIZE - NAME_POOL.qsize()):
            read_name = name_reader().send # Make generater.
            read_name(None) # Initalize with None.
            NAME_POOL.put_nowait(read_name)

        # Make sure that we are not over NAME_POOL_SIZE
        while NAME_POOL_SIZE < NAME_POOL.qsize():
            # To large?
            # Pull
            NAME_POOL.get_nowait()

    except queue.Full:
        # Somehow, NAME_POOL_SIZE must have changed?
        logging.error("NAME_POOL_SIZE changed during pool initalization.")

    except queue.Empty:
        # Hummmm.
        # Two Possibilities
        # 1 NAME_POOL_SIZE is somehow less than zero.
        # Or NAME_POOL.qsize was wrong (changed do to mulithreading.)
        if NAME_POOL_SIZE <= 0:
            logging.fatal("NAME_POOL_SIZE is %d. Which is not greater than zero." % NAME_POOL_SIZE)
        else:
            logging.error("NAME_POOL.qsize() changed during initalization.")

    try:
        for i in range(TIME_POOL_SIZE - TIME_POOL.qsize()):
            read_time = time_reader().send # Make generater.
            read_time(None) # Initalize with None.
            TIME_POOL.put_nowait(read_time)

        # Make sure that we are not over TIME_POOL_SIZE
        while TIME_POOL_SIZE < TIME_POOL.qsize():
            # To large?
            # Pull
            TIME_POOL.get_nowait()

    except queue.Full:
        # Somehow, TIME_POOL_SZE must have changed?
        logging.error("TIME_POOL_SIZE changed during pool initalization.")

    except queue.Empty:
        # Hummmm.
        # Two Possibilities
        # 1 TIME_POOL_SIZE is somehow less than zero.
        # Or TIME_POOL.qsize was wrong (changed do to mulithreading.)
        if TIME_POOL_SIZE <= 0:
            logging.fatal("TIME_POOL_SIZE is %d. Which is not greater than zero." %
                          TIME_POOL_SIZE)
        else:
            logging.error("TIME_POOL.qsize() changed during initalization.")

def deinit():
    """Deinitalize the processor."""
    # This frees up the memory and closes the cv2 windows.
    NAME_POOL = queue.Queue(NAME_POOL_SIZE)
    TIME_POOL = queue.Queue(TIME_POOL_SIZE)
    cv2.destroyAllWindows()
    
def read_image(image):#, debug = False):
    """Take image files and try to read the words from them.
       Takes a numpy image.
    """
    assert not NAME_POOL.empty(), "process_frames.NAME_POOL not initalized."
    assert not TIME_POOL.empty(), "process_frames.TIME_POOL not initalized."

    # Verify this is a valid image.
    if not is_numpy_image(image):
        # Error, bad image.
        raise TypeError("Image should have been a numpy array, not %r." % image)

    # Extract the 2 portions with information.
    # Crop numpy image. NOTE: its img[y: y + h, x: x + w]
    nx, ny, nw, nh = MATCH_NAME_RECT
    tx, ty, tw, th = MATCH_TIME_RECT
    # Take into effect the scaling factor of the screen size.
    dx, dy = DEFAULT_SIZE
    iy, ix, _ = image.shape # Y and X sizes. There is a third argument which
    # I think is color depth?
    
    # Calculate a scale factor. Assume a cropping on the horizontal if needed.
    r_x, r_y = ix * 1. / dx, iy * 1. / dy
    # Actually, r_y is more reliable.
    r_x = r_y
    assert r_x != 0 and r_y != 0
    name_top,    time_top   = int(floor(ny * r_y)),   int(floor(ty * r_y))
    name_left,   time_left  = int(floor(nx * r_x)),   int(floor(tx * r_x))
    name_bottom, time_bottom= int(ceil((ny+nh)*r_y)), int(ceil((ty+th)*r_y))
    name_right,  time_right = int(ceil((nx+nw)*r_x)), int(ceil((tx+tw)*r_x))
    assert all([name_top,    time_top,   name_left, time_left,
                name_bottom, time_bottom,name_right,time_right])
    
    # Where it matters, make the box a little larger for rounding error.
##    name_frame = image[ny : ny + nh, nx : nx + nw]
##    time_frame = image[ty : ty + th, tx : tx + tw]
    name_frame = image[name_top : name_bottom, name_left : name_right]
    time_frame = image[time_top : time_bottom, time_left : time_right]
##    del image # Its a full image in memory. Clear as fast as possible.

    # For testing.
    if DEBUG:
        cv2.imshow("Name", name_frame)
        cv2.imshow("Time", time_frame)

    # Turns out an enlargment significantly helps the readability of the frames

    # To get the NAME from the image.
    # Enlarge the frames and to the extraction.
    name_image = Image.fromarray(enlarge(name_frame, REG_NAME_ENLARGE))
    # Get the reader from the pool to read.
    read_name = NAME_POOL.get()
    # Remove unicode if present.
    name_raw  = str(read_name(name_image))
    try:
        NAME_POOL.put_nowait(read_name)
    except queue.Full:
        logging.error("Could not put name reader back in pool.")

    # Smart read name.
    name = smart_read_name(name_raw)

    if not name:
        # We are done, negative match.
        time_raw = "NA"
        time_ext = "NA"
        time     = None
    else:
        # Otherwise, analyize time.
        # Enlarge the frames and to the extraction.
        time_image     = Image.fromarray(
            enlarge(time_frame,               REG_TIME_ENLARGE))
        try:
            time_ext_image = Image.fromarray(
                enlarge(extract_image(time_frame),EXT_TIME_ENLARGE))
        except TypeError:
            # Rarely, this can fail when there are no contour lines found.
            # The extracted just should be the same.
            logging.error("Image Extraction failed with error %r." % sys.exc_value)
            time_ext_image = time_image

        read_time = TIME_POOL.get()
        # Remove unicode if present.
        time_raw  = str(read_time(time_image))
        time_ext  = str(read_time(time_ext_image))
        try:
            TIME_POOL.put_nowait(read_time)
        except queue.Full:
            logging.error("Could not put time reader back in pool.")

        time = smart_read_time(time_raw, time_ext)


     # Convert time to number.
    if time is not None and time.isdigit():
        time = int(time)
    else:
        time = None

    # Log the initial reading and conversion.
    # INFO:root:Name Read: 'Qualmution 5 M 78\n\n'   -> 'Qualification 5 of 78'.
    # INFO:root:Time Read: '13 \n\n' (' 3 \n\n')     -> '13'.
    logging.info("Name Read: %-28r"      " -> %s" % (name_raw, name))
    logging.info("Time Read: %-13r (%-12r) -> %s" % (time_raw, time_ext, time))

    return name, time
