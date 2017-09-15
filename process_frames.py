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
import tesserocr
from PIL import Image
from numpy import ndarray
from extract_lib import extract_image
# Format: (x, y, width, height) Assumed frame size (512, 288)
match_name_rect = (107, 224, 103, 16)
match_time_rect = (244, 243, 28, 13)

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
__version__ = "0.5"

REG_NAME_ENLARGE = 5
REG_TIME_ENLARGE = 20
EXT_TIME_ENLARGE = 14

ADAPTIVE_CLASSIFIER = True
ALLOW_FAILURE = True

# Basically, try to convert everything to one of these formats.
NAME_FORMATS = (    "",                           "Test Match",
                    "Qualification # of #",       "Quarterfinal # of #",
                    "QuarterFinal Tiebreaker #",  "Semifinal #",
                    "Semifinal # of #",           "Final #",
                    "Practice # of #")

NAME_CHAR_LIST = "".join(sorted(set("".join(NAME_FORMATS)).difference("#")))

NUMBER_CORRENTIONS = {
    # This is a list of non-number letters and numbers that are
    # sometimes accidently encoded as them.
    "s" : "5",
    "S" : "5",
    "1a": "78", # Evidently a mistake the system will make
    
    }

def is_numpy_image(image):
    """Check that the image is a numpy image, or really an array of pixels."""
    return isinstance(image, ndarray)

def similar(a, b):
    """Evaluate the similarity of two strings."""
    # This is built into python. Python is Great!!!
    return difflib.SequenceMatcher(None, a, b).ratio()

def enlarge(image, ratio):
    """Take the image and increase the size by ratio."""
    return cv2.resize(src = image, dsize = (0,0), fx = ratio, fy = ratio)

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
       
def smart_read_name(name_text):
    """Post Process the name text."""
    # First clean reg_name a little bit.
    name_text = name_text.strip()
    match_name = re.sub("\\s+", " ", name_text)

    # Take the reg_name, put # in for numbers for compare.
    reg_name_template, n = re.subn("\\d+", "#", match_name)
    
    match = difflib.get_close_matches(reg_name_template, NAME_FORMATS,
                                      n = 1, # At most only one result.
##                                      cutoff =.4
##                                      #Particularly Practice needs this.
                                      )
    del reg_name_template
    if not match:
        return "" # We are done here.
    else:
        match = match[0]
    # So, we have our closest possibility, and our raw input.
    # Try to extract the numbers.
    if n == match.count("#"):
        # We are good, the each number present has a place. Pull them out
        # and shove them into the other.
        for num in re.findall("\\d+", match_name):
            match = match.replace("#", num, 1)
        return match
    else:
        # Well, the numbers don't match?
        # Well, more reliable than the numbers, is the spacings.
        raw_words = name_text.split(" ")
        known_words = list(match.split(" "))
        if len(raw_words) != len(known_words):
            # Ok, wrong number of numbers AND words.
            # Not parseable.
            if ALLOW_FAILURE:
                return None
            else:
                return name_text
        else:
            # The pieces line up. To continue find the "#" pieces and try
            # to make smart substitutions.
            for i in range(len(known_words)):
                if known_words[i] == "#":
                    raw_word = raw_words[i]
                    if raw_word.isdigit():
                        # This is not the problem. Assert this as normal.
                        known_words[i] = raw_word
                    else:
                        # Substitute the number, after working on it.
                        sub = NUMBER_CORRENTIONS.get(raw_words[i], None)
                        if sub is None:
                            # Ok, no idea of what to substitute.
                            # I am done!
                            if ALLOW_FAILURE:
                                return None
                            else:
                                return name_text
                        else:
                            known_words[i] = sub
                # Otherwise skip and keep going.
            # Now return known_words because that is our best option.
            return ' '.join(known_words)
        return match_name

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
            logging.fatal("TIME_POOL_SIZE is %d. Which is not greater than zero." % TIME_POOL_SIZE)
        else:
            logging.error("TIME_POOL.qsize() changed during initalization.")

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
##    if debug:
##        global name, time_reg, time_ext
    #img_file = os.path.join(IMAGE_FOLDER, img_file)
    #orig_frame = cv2.imread(img_file)
    
    # Extract the 2 portions with information.
    # Crop numpy image. NOTE: its img[y: y + h, x: x + w]
    nx, ny, nw, nh = match_name_rect
    tx, ty, tw, th = match_time_rect
    name_frame = image[ny: ny + nh, nx: nx + nw]
    time_frame = image[ty: ty + th, tx: tx + tw]
    del image # Its a full image in memory. Clear as fast as possible.

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
        time     = ""
    else:
        # Otherwise, analyize time.
        # Enlarge the frames and to the extraction.
        time_image     = Image.fromarray(
            enlarge(time_frame,               REG_TIME_ENLARGE))
        time_ext_image = Image.fromarray(
            enlarge(extract_image(time_frame),EXT_TIME_ENLARGE))

        read_time = TIME_POOL.get()
        # Remove unicode if present.
        time_raw  = str(read_time(time_image))
        time_ext  = str(read_time(time_ext_image))
        try:
            TIME_POOL.put_nowait(read_time)
        except queue.Full:
            logging.error("Could not put time reader back in pool.")

        time = smart_read_time(time_raw, time_ext)
    # Log the initial reading and conversion.
    # INFO:root:Name Read: 'Qualmution 5 M 78\n\n'   -> 'Qualification 5 of 78'.
    # INFO:root:Time Read: '13 \n\n' (' 3 \n\n')     -> '13'.
    logging.info("Name Read: %-28r"      " -> %r" % (name_raw, name))
    logging.info("Time Read: %-13r (%-12r) -> %r" % (time_raw, time_ext, time))

    return name, time
