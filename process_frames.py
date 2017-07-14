#!/bin/env python
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
    
__all__ = ["read_image", "VERBOSE", "REG_NAME_ENLARGE",
           "REG_TIME_ENLARGE", "EXT_TIME_ENLARGE", "ADAPTIVE_CLASSIFIER"]

REG_NAME_ENLARGE = 5
REG_TIME_ENLARGE = 20
EXT_TIME_ENLARGE = 14

ADAPTIVE_CLASSIFIER = False
ALLOW_FAILURE = True

# Basically, try to convert everything to one of these formats.
NAME_FORMATS = (    "",                           "Test Match",
                    "Qualification # of #",       "Quarterfinal # of #",
                    "QuarterFinal Tiebreaker #",  "Semifinal #",
                    "Semifinal # of #",           "Final #")

NUMBER_CORRENTIONS = {
    # This is a list of non-number letters and numbers that are
    # sometimes accidently encoded as them.
    "s" : "5",
    "S" : "5",
    "1a": "78", # Evidently a mistake the system will make
    
    }

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
    char_list = " 0123456789MPQTacefhilmnopqstuy"

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

read_name = name_reader().send
read_time = time_reader().send

# Start the functions by passing None
read_name(None)
read_time(None)
       
def smart_read_name(name_text):
    """Post Process the name text."""
    # First clean reg_name a little bit.
    name_text = name_text.strip()
    match_name = re.sub("\\s+", " ", name_text)

    # Take the reg_name, put # in for numbers for compare.
    reg_name_template, n = re.subn("\\d+", "#", match_name)
    
    match = difflib.get_close_matches(reg_name_template, NAME_FORMATS, 1)
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
    # If the extracted value is blank then this is blank unless
    # regular time is at least 3 characters.
    if not ext_time and len(reg_time) <= 2:
        # No text found. Probably no text at all.
        return ""
    # Now, also. If extracted value has a number but regular time is blank,
    # Use the extracted value.
    if not reg_time:
        time = ext_time
    else:
        time = reg_time
    
    time = time.strip()
    if time.isdigit() and (time[0] != "0" or time == "0"):
        return time
    if ALLOW_FAILURE:
        return ""
    else:
        return None

def read_image(image, debug = False):
    """Take image files and try to read the words from them.
       Takes a numpy image.
    """
    if debug:
        global name, time_reg, time_ext
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
    
    # Enlarge the frames and to the extraction.
    name    = read_name(Image.fromarray(enlarge(name_frame, REG_NAME_ENLARGE)))
    time_reg= read_time(Image.fromarray(enlarge(time_frame, REG_TIME_ENLARGE)))
    time_ext= read_time(Image.fromarray(enlarge(extract_image(time_frame),EXT_TIME_ENLARGE)))

    name = smart_read_name(name)
    time = smart_read_time(time_reg, time_ext) if name != "" else ""

    logging.info("Image Results Name: %s Time: %s" % (name, time))
    
    return name, time

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
class 
def read_moment(video, timestamp):
    """Read text at a timestamped moment (seconds in the video)."""
    pass
