"""
Takes an video file (very long) and slowly pulls the matches in the video out
and makes those seperate files.
"""
# Configure logging.
import logging

logging.basicConfig(
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
