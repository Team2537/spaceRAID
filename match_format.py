"""
Take the created match from parse and save it to a file.
To offer the best compatabiliy and usefulness, this supports csv, json, and xml.

To accomplish this, the pandas library is used to convert the formats.
It may be computationally easier to use the libraries directly, but this will
give better upgradability.

The results should be a dictionary with timestamps as keys and values of the
reading results.

Actually, considing panda is HUGE and xml isn't even supported, just switching
to json library for now for just json support.
"""
import os
##import pandas as pd
##from io import StringIO
##
##def load(file, type = None):
##    if type is None:
##        type = os.path.splitext(file)
##    if type == "csv":
##        table = pd.read_csv(file)
##    elif type == "json":
##        table = pd.read_json(file)
##    elif type == "xml":
##        table = pd.read_sql

##import json
##
##def load(file):
##    json.load(
#
# Screw it. Json is so simple, this can just go in the parser.
