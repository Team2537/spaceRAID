"""
EasyGuiRevisionInfo = "version 0.83 2008-06-12"

EasyGui provides an easy-to-use interface for simple GUI interaction
with a user.  It does not require the programmer to know anything about
tkinter, frames, widgets, callbacks or lambda.  All GUI interactions are
invoked by simple function calls that return results.

Documentation is in an accompanying file, easygui.txt.

WARNING about using EasyGui with IDLE
=====================================

You may encounter problems using IDLE to run programs that use EasyGui. Try it
and find out.  EasyGui is a collection of Tkinter routines that run their own
event loops.  IDLE is also a Tkinter application, with its own event loop.  The
two may conflict, with the unpredictable results. If you find that you have
problems, try running your program outside of IDLE.

Note that EasyGui requires Tk release 8.0 or greater.
"""

# Because easygui has stopped working reliably on macOS, this is an alternative
# library that uses the command line to mimic the performance but gets input
# from the command line.

# A base version of easygui from 2.5 is used to build from. This is prefered
# because this version of easygui was inclosed in a single file.
EasyGuiRevisionInfo = "version .9 2017-08-19"

DefaultColumnWidth = 72 # Can be increased some.

# see easygui.txt for revision history information

__all__ = [
      'ynbox'          ,'ccbox'            ,'boolbox',          'indexbox'    ,
      'msgbox'         ,'buttonbox'        ,'integerbox',       'multenterbox',
      'enterbox'       ,'choicebox'        ,'codebox',          'textbox'     ,
      'diropenbox'     ,'fileopenbox'      ,'filesavebox',      'passwordbox' ,
      'multpasswordbox','multchoicebox'    ,'abouteasygui',
      # Now the one new changed function. This is the only high level difference
      # between easygui and dummy_easygui.
      'tkinter_check'
    ]

# Python 2 and Python 3 compatibility.
try:
    raw_input
except ImportError:
    raw_input = input

import sys, os

def dq(s): return '"%s"' % s

import string

#-----------------------------------------------------------------------
# tkinter_check
#-----------------------------------------------------------------------
def tkinter_check():
    """Check is tkinter is stable and the standard easygui library
       can be used or if this dummy should be used.
    """
    # Currently, easygui works in python 2.5 and I guess older.
    return sys.version_info[:2] <= (2, 5)

#-----------------------------------------------------------------------
# various boxes built on top of the basic buttonbox
#-----------------------------------------------------------------------

#-----------------------------------------------------------------------
# ynbox
#-----------------------------------------------------------------------
def ynbox(msg="Shall I continue?", title=" ", choices=("Yes","No"), image=None):
    """
    Display a msgbox with choices of Yes and No.

    The default is "Yes".

    The returned value is calculated this way::
        if the first choice ("Yes") is chosen, or if the dialog is cancelled:
            return 1
        else:
            return 0

    If invoked without a msg argument, displays a generic request for a confirmation
    that the user wishes to continue.  So it can be used this way::
        if ynbox(): pass # continue
        else: sys.exit(0)  # exit the program

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    return boolbox(msg, title, choices, image=None)

#-----------------------------------------------------------------------
# ccbox
#-----------------------------------------------------------------------
def ccbox(msg="Shall I continue?",title=" ",choices=("Continue","Cancel"),image=None):
    """
    Display a msgbox with choices of Continue and Cancel.

    The default is "Continue".

    The returned value is calculated this way::
        if the first choice ("Continue") is chosen, or if the dialog is cancelled:
            return 1
        else:
            return 0

    If invoked without a msg argument, displays a generic request for a confirmation
    that the user wishes to continue.  So it can be used this way::

        if ccbox():
            pass # continue
        else:
            sys.exit(0)  # exit the program

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    return boolbox(msg, title, choices, image = None)

#-----------------------------------------------------------------------
# boolbox
#-----------------------------------------------------------------------
def boolbox(msg="Shall I continue?",title=" ",choices=("Yes","No"),image=None):
    """
    Display a boolean msgbox.

    The default is the first choice.

    The returned value is calculated this way::
        if the first choice is chosen, or if the dialog is cancelled:
            returns 1
        else:
            returns 0
    """
    reply = buttonbox(msg = msg, choices = choices, title = title, image = None)
    if reply == choices[0]: return 1
    else: return 0

#-----------------------------------------------------------------------
# indexbox
#-----------------------------------------------------------------------
def indexbox(msg="Shall I continue?",title=" ",choices=("Yes","No"),image=None):
    """
    Display a buttonbox with the specified choices.
    Return the index of the choice selected.
    """
    reply = buttonbox(msg=msg, choices=choices, title=title, image=None)
    index = -1
    for choice in choices:
        index = index + 1
        if reply == choice: return index
    raise AssertionError(
        "There is a program logic error in the EasyGui code for indexbox.")

#-----------------------------------------------------------------------
# msgbox
#-----------------------------------------------------------------------
def msgbox(msg="(Your message goes here)",title=" ",ok_button="OK",image=None):
    """
    Display a messagebox
    """
    if type(ok_button) != type("OK"):
        raise AssertionError("The 'ok_button' argument to msgbox must be a string.")

    return buttonbox(msg=msg, title=title, choices=[ok_button], image=image)

#-------------------------------------------------------------------
# buttonbox
#-------------------------------------------------------------------
def buttonbox(msg="",title=" ",choices=("Button1","Button2","Button3"),image=None):
    """
    Display a msg, a title, and a set of buttons.
    The buttons are defined by the members of the choices list.
    Return the text of the button that the user selected.

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    # Image is kept for compatibility but will do nothing. Also, I don't
    # think it even was documented with easygui.
    if title.strip():
        for line in title.split("\n"):
            print(line)
    # Ok, I will admit, this for loop could be replaced with.
    ## print(line)
    # However, I like the scrolling of the text.
    for line in msg.split("\n"):
        print(line)

    # Print the choices that need to selected from.
    # This will be printed across each row instead of strait down.
    # This requires some more figureing.
    line = ""
    for i, choice in enumerate(choices):
        choice = ("%d: %s " + " " * 4) % (i + 1, choice)
        # See if this choice can be added to the existing line.
        if len(line) + len(choice) + 8 < DefaultColumnWidth:
            line += " " * 4 + choice
        else:
            # Line is too long so print it and start a new line.
            print(string.center(line, DefaultColumnWidth))
            line = choice
    else:
        # Make sure the last section of the last line is printed.
        print(string.center(line, DefaultColumnWidth))

    try:
        # Now ask for input.
        replyButtonText = None
        userQuestion = "What is your answer?: "
        while replyButtonText is None:
            # Get answer from user.
            replyButtonText = raw_input(userQuestion)

            # Figure out if this is a usable input.

            # Check if this is a number which responds to the number of an answer.
            # The check if the number is a logical answer with the number of
            # choices. If so, make the responce the corrosponding choice.
            if replyButtonText.isdigit()and 1<=int(replyButtonText)<=len(choices):
                replyButtonText = choices[int(replyButtonText) - 1]

            # If this fails, check if the answer is a choice. If so, great.
            # Otherwise, give an error message and reset replyButtonText to None
            # because the answer was not valid.
            elif replyButtonText not in choices:
                # Not valid answer.
                # Responce changes depending on the number of items in choices.

                # Also, if there is only one button, as some dialog boxes use.
                # Just return that choice and don't bother with this loop.
                if len(choices) == 1:
                    # Only one option, don't bother complaining.
                    replyButtonText = choices[0]
                else:
                    if len(choices) == 2: # 2 Item answer.
                        userQuestion = ( # Yes, it is hard coded.
                            "Sorry, %r is not a valid answer.\n"
                            "Your answer must be 1 or 2, or one of the choices.\n"
                            "What is your answer?: " % replyButtonText)
                    elif len(choices) <= 10:
                        userQuestion = (
                            "Sorry, %r is not a valid answer.\n"
                            "Your answer must be %s, or one of the choices.\n"
                            "What is your answer?: " % (replyButtonText,
                                #######################################
                                # Create a sequence like "1, 2, 3 or 4"
                                ", ".join(map(str, range(1, len(choices))))
                                + " or " + str(len(choices))
                                #######################################
                                                        )
                            )
                    else:
                        userQuestion = (
                            "Sorry, %r is not a valid answer.\n"
                            "Your answer must be of 1 through %d or one of the choices.\n"
                            "What is your answer?: " % (replyButtonText, len(choices)))
                    replyButtonText = None # Force another round of asking questions.

    except KeyboardInterrupt:
        # Operation was canceled.
        # Return the first choice.
        replyButtonText = choices[0]

    # Dumb check to make sure things are working fine.
    assert replyButtonText in choices, (
        "There is a program logic error in the EasyGui code for buttonbox.")

    return replyButtonText

#-------------------------------------------------------------------
# integerbox
#-------------------------------------------------------------------
def integerbox(msg="", title=" ", default="", argLowerBound=0, argUpperBound=99):
    """
    Show a box in which a user can enter an integer.

    In addition to arguments for msg and title, this function accepts
    integer arguments for default_value, lowerbound, and upperbound.

    The default_value argument may be None.

    When the user enters some text, the text is checked to verify
    that it can be converted to an integer between the lowerbound and upperbound.

    If it can be, the integer (not the text) is returned.

    If it cannot, then an error msg is displayed, and the integerbox is
    redisplayed.

    If the user cancels the operation, None is returned.
    """
    if default != "":
        if type(default) != type(1):
            raise AssertionError(
                "integerbox received a non-integer value for "
                + "default of " + dq(str(default)) , "Error")

    if type(argLowerBound) != type(1):
        raise AssertionError(
            "integerbox received a non-integer value for "
            + "argLowerBound of " + dq(str(argLowerBound)) , "Error")

    if type(argUpperBound) != type(1):
        raise AssertionError(
            "integerbox received a non-integer value for "
            + "argUpperBound of " + dq(str(argUpperBound)) , "Error")

    if msg == "":
        msg = ("Enter an integer between " + str(argLowerBound)
            + " and "
            + str(argUpperBound)
            )

    while 1:
        reply = enterbox(msg, title, str(default))
        if reply == None: return None

        try:
            reply = int(reply)
        except:
            msgbox ("The value that you entered:\n\t%s\nis not an integer." % dq(str(reply))
                    , "Error")
            continue

        if reply < argLowerBound:
            msgbox ("The value that you entered is less than the lower bound of "
                + str(argLowerBound) + ".", "Error")
            continue

        if reply > argUpperBound:
            msgbox ("The value that you entered is greater than the upper bound of "
                + str(argUpperBound) + ".", "Error")
            continue

        # reply has passed all validation checks.
        # It is an integer between the specified bounds.
        return reply

#-------------------------------------------------------------------
# multenterbox
#-------------------------------------------------------------------
def multenterbox(msg="Fill in values for the fields.", title=" "
    , fields  = (), values = () ):
    """
Show screen with multiple data entry fields.

If there are fewer values than names, the list of values is padded with
empty strings until the number of values is the same as the number of names.

If there are more values than names, the list of values
is truncated so that there are as many values as names.

Returns a list of the values of the fields,
or None if the user cancels the operation.

Here is some example code, that shows how values returned from
multenterbox can be checked for validity before they are accepted::
    ----------------------------------------------------------------------
    msg = "Enter your personal information"
    title = "Credit Card Application"
    fieldNames = ["Name","Street Address","City","State","ZipCode"]
    fieldValues = []  # we start with blanks for the values
    fieldValues = multenterbox(msg,title, fieldNames)

    # make sure that none of the fields was left blank
    while 1:
        if fieldValues == None: break
        errmsg = ""
        for i in range(len(fieldNames)):
            if fieldValues[i].strip() == "":
                errmsg = errmsg + ('"%s" is a required field.\n\n' % fieldNames[i])
        if errmsg == "": break # no problems found
        fieldValues = multenterbox(errmsg, title, fieldNames, fieldValues)

    print "Reply was:", fieldValues
    ----------------------------------------------------------------------

@arg msg: the msg to be displayed.
@arg title: the window title
@arg fields: a list of fieldnames.
@arg values:  a list of field values
"""
    return __multfillablebox(msg,title,fields,values,None)


#-----------------------------------------------------------------------
# multpasswordbox
#-----------------------------------------------------------------------
def multpasswordbox(msg="Fill in values for the fields.", title=" "
    , fields  = (), values = ()  ):
    """
Same interface as multenterbox.  But in multpassword box,
the last of the fields is assumed to be a password, and
is masked with asterisks.

Here is some example code, that shows how values returned from
multpasswordbox can be checked for validity before they are accepted::
----------------------------------------------------------------------
msg = "Enter logon information"
title = "Demo of multpasswordbox"
fieldNames = ["Server ID", "User ID", "Password"]
fieldValues = []  # we start with blanks for the values
fieldValues = multpasswordbox(msg,title, fieldNames)

# make sure that none of the fields was left blank
while 1:
    if fieldValues == None: break
    errmsg = ""
    for i in range(len(fieldNames)):
        if fieldValues[i].strip() == "":
            errmsg = errmsg + ('"%s" is a required field.\n\n' % fieldNames[i])
    if errmsg == "": break # no problems found
    fieldValues = multpasswordbox(errmsg, title, fieldNames, fieldValues)

print "Reply was:", fieldValues
----------------------------------------------------------------------
"""
    return __multfillablebox(msg,title,fields,values,"*")

#-----------------------------------------------------------------------
# __multfillablebox
#-----------------------------------------------------------------------
def __multfillablebox(msg="Fill in values for the fields.", title=" "
    , fields=(), values=(), argMaskCharacter = None ):

    fields = list(fields) # Make sure it is a list.
    values = list(values) # Make sure it is a list.

    choices = ["OK", "Cancel"]
    if len(fields) == 0: return None

    if   len(values) == len(fields): pass
    elif len(values) >  len(fields):
        fields = fields[0:len(values)]
    else:
        while len(values) < len(fields):
            values.append("")

    # Print the title, if there is in fact, a title.
    if title.strip():
        print(title)

    # Print the message.
    # Again scrolling fashion.
    ##print(msg)
    # Would also work.
    for line in msg.split("\n"):
        print(line)

    entries = []

    # Ask for feedback on each field.
    for i, (field, value) in enumerate(zip(fields, values)):
        if value:
            userQuestion = "%s (Default %r): " % (field, value)
        else:
            userQuestion = "%s: " % field

        # Check if this is a password box.
        if argMaskCharacter and len(fields) - 1 == i:
            from getpass import getpass
            userAnswer = getpass(userQuestion)
        else:
            userAnswer = raw_input(userQuestion)

        if not userAnswer and value:
            # No answer, substitute value.
            userAnswer = value

        entries.append(userAnswer)

    return entries

#-------------------------------------------------------------------
# enterbox
#-------------------------------------------------------------------
def enterbox(msg="Enter something.", title=" ", default="",strip=True):
    """
    Show a box in which a user can enter some text.

    You may optionally specify some default text, which will appear in the
    enterbox when it is displayed.

    Returns the text that the user entered, or None if he cancels the operation.

    By default, enterbox strips its result (i.e. removes leading and trailing
    whitespace).  (If you want it not to strip, use keyword argument: strip=False.)
    This makes it easier to test the results of the call::

        reply = enterbox(....)
        if reply:
            ...
        else:
            ...
    """
    result = __fillablebox(msg, title, default=default, argMaskCharacter=None)
    if result and strip:
        result = result.strip()
    return result


def passwordbox(msg="Enter your password.", title=" ", default=""):
    """
    Show a box in which a user can enter a password.
    The text is masked with asterisks, so the password is not displayed.
    Returns the text that the user entered, or None if he cancels the operation.
    """
    return __fillablebox(msg, title, default, "*")


def __fillablebox(msg, title="", default="", argMaskCharacter=None):
    """
    Show a box in which a user can enter some text.
    You may optionally specify some default text, which will appear in the
    enterbox when it is displayed.
    Returns the text that the user entered, or None if he cancels the operation.
    """
    if title == None: title == ""
    if default == None: default = ""

    # Print title if there is a title.
    if title:
        print(title)

    # Now the message.
    # Scr
    #    oll
    #       ing
    #           style.
    for line in msg.split("\n"):
        print(line)

    # Now get input.
    if default:
        userQuestion = "What is your answer? (Default) %r: " % default
    else:
        userQuestion = "What is your answer?: "

    try:
        if argMaskCharacter:
            from getpass import getpass
            return getpass(userQuestion)
        else:
            return raw_input(userQuestion)
    except KeyboardInterrupt:
        # No data, just an error.
        return None

#-------------------------------------------------------------------
# multchoicebox
#-------------------------------------------------------------------
def multchoicebox(msg="Pick as many items as you like.",title=" ",choices=(),**kwargs):
    """
    Present the user with a list of choices.
    allow him to select multiple items and return them in a list.
    if the user doesn't choose anything from the list, return the empty list.
    return None if he cancelled selection.

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    if len(choices) == 0:
        choices = ["Program logic error - no choices were specified."]

    global __choiceboxMultipleSelect
    __choiceboxMultipleSelect = 1
    return __choicebox(msg, title, choices)


#-----------------------------------------------------------------------
# choicebox
#-----------------------------------------------------------------------
def choicebox(msg="Pick something.",title=" ",  choices=(),  buttons=()):
    """
    Present the user with a list of choices.
    return the choice that he selects.
    return None if he cancels the selection selection.

    @arg msg: the msg to be displayed.
    @arg title: the window title
    @arg choices: a list or tuple of the choices to be displayed
    """
    if len(choices) == 0:
        choices = ["Program logic error - no choices were specified."]

    global __choiceboxMultipleSelect
    __choiceboxMultipleSelect = 0
    return __choicebox(msg,title,choices,buttons)

#-----------------------------------------------------------------------
# __choicebox
#-----------------------------------------------------------------------
def __choicebox(msg, title, choices,  buttons=()):
    """
    internal routine to support choicebox() and multchoicebox()
    """
    #-------------------------------------------------------------------
    # If choices is a tuple, we make it a list so we can sort it.
    # If choices is already a list, we make a new list, so that when
    # we sort the choices, we don't affect the list object that we
    # were given.
    #-------------------------------------------------------------------
    choices = list(choices[:])
    if len(choices) == 0: choices = ["Program logic error - no choices were specified."]

    # make sure all choices are strings
    for index in range(len(choices)):
        choices[index] = str(choices[index])

    # No buttons to speach of on this display.
    # So don't do any processing with buttons.


    #---------------------------------------------------
    # sort the choices
    # eliminate duplicates
    #---------------------------------------------------
    for index in range(len(choices)):
        choices[index] == str(choices[index])

    # Optimized sort from the original (preserved here)
    ##choices.sort(lambda x,y: cmp(x.lower(), y.lower()))#case-insensitive sort
    choices.sort(None, str.lower) # case-insensitive sort

    lastInserted = None
    # Neat little piece of code to remove repeat possiblities.
    choiceboxChoices = []
    for choice in choices:
        if choice == lastInserted: pass
        else:
            choiceboxChoices.append(choice)
            lastInserted = choice

    if title.strip():
        print(title)
    # Ok, I will admit, this for loop could be replaced with.
    ## print(line)
    # However, I like the scrolling of the text.
    for line in msg.split("\n"):
        print(line)

    # Print the choices that need to selected from.
    for i, choice in enumerate(choices):
        print("%d: %s" % (i + 1, choice))

    try:
        # Varibles
        replyButtonText = None
        selectedChoices = []
        userQuestion = "What is your answer?: "

        if __choiceboxMultipleSelect:
            # Multiple Select, print info on Multi Select and "Select All" and
            # "Invert All". (Before it was "Clear All") but that wouldn't work.
            print('Type "Select All", "All", or "S" to select all and "Invert All"')
            print('or "I" to invert selection. Otherwise, enter a comma')
            print('seperated list of choices.')

            while replyButtonText is None:
                # Get answer from user.
                replyButtonText = raw_input(userQuestion).strip()

                # First, check if the input is S(elect All)
                if replyButtonText.lower() in ("s", "select all", "all"):
                    # Well that was easy.
                    selectedChoices.extend(choices)

                else:
                    invertSelection = False
                    for reply in replyButtonText.split(","):
                        # Remove spaces.
                        reply = reply.strip()

                        # If this is a number, add it to the list.
                        if reply.isdigit() and 1 <= int(reply) <= len(choices):
                            selectedChoices.append(choices[int(reply) - 1])

                        # Else, is this INVERT?
                        elif reply.lower() in ("i", "invert", "invert all"):
                            invertSelection = True

                        # Otherwise, give an error message and go around again.
                        else:
                            userQuestion = (
                        "Sorry, %s is not a valid answer. Your answer must be\n"
                        "1 through %d. What is your answer?: " % len(choices))
                            invertSelection = False # Reset
                            selectedChoices = [] # Reset
                            replyButtonText = None # Reset
            # If invertSelection, got turned on, invert the selection.
            if invertSelection:
                  selectedChoices = list(set(selectedChoices).difference(choices))

        else:
            # No multiselect, this is simple.
            print('Type the number of your selection.')

            while replyButtonText is None:
                # Get answer from user.
                replyButtonText = raw_input(userQuestion)

                # Check if this is a number. Then check if the number is logical
                # with the number of choices. If so, make the responce the
                # corrosponding choice.
                if (replyButtonText.isdigit() and
                    1 <= int(replyButtonText) <= len(choices)):
                    selectedChoices = choices[int(replyButtonText) - 1]

                else:
                     # Not valid answer.
                    userQuestion = (
                        "Sorry, %s is not a valid answer. Your answer must be\n"
                        "1 through %d. What is your answer?: " %
                        (replyButtonText, len(choices)))

                    replyButtonText = None # Force another round of asking questions.

    except KeyboardInterrupt:
        # Operation was canceled.
        # Return the first choice.
        return None

    return selectedChoices

#-------------------------------------------------------------------
# codebox
#-------------------------------------------------------------------

def codebox(msg="", title=" ", text=""):
    """
    Display some text in a monospaced font, with no line wrapping.
    This function is suitable for displaying code and text that is
    formatted using spaces.

    The text parameter should be a string, or a list or tuple of lines to be
    displayed in the textbox.
    """
    textbox(msg, title, text, codebox=1)

#-------------------------------------------------------------------
# textbox
#-------------------------------------------------------------------
def textbox(msg="", title=" ", text="", codebox=0):
    """
    Display some text in a proportional font with line wrapping at word breaks.
    This function is suitable for displaying general written text.

    The text parameter should be a string, or a list or tuple of lines to be
    displayed in the textbox.
    """

    if msg == None: msg = ""
    if title == None: title = ""

    # Very simple. Print the message and ask for a button press to continue.

    try:
        # Print title.
        if title.strip():
            print(title)

        # Print Message Scrolling style.
        for line in msg.split("\n"):
            print("\t"+line)

        if not codebox:
            # Now print text.
            for line in text.split("\n"):
                print(line)
        # Codebox, print one character at a time.
        else:
            for char in text:
                sys.stdout.write(char)
                sys.stdout.flush()

        raw_input("Press enter to continue.")
    except KeyboardInterrupt:
        # Well, that works too.
        pass

#-------------------------------------------------------------------
# diropenbox
#-------------------------------------------------------------------
def diropenbox(msg=None, title=None, default=None):
    """
    A dialog to get a directory name.
    Note that the msg argument, if specified, is ignored.

    Returns the name of a directory, or None if user chose to cancel.

    If the "default" argument specifies a directory name,
    and that directory exists,
    then the dialog box will start with that directory.
    """
    if title:
        print(title)
    for line in msg.split("\n"):
        print(line)
    try:
        f = raw_input("Directory: ")
    except KeyboardInterrupt:
        f = None
    if not f: return None
    return os.path.normpath(f)


#-------------------------------------------------------------------
# fileopenbox
#-------------------------------------------------------------------
def fileopenbox(msg=None, title=None, default=None):
    """
    A dialog to get a file name.
    Returns the name of a file, or None if user chose to cancel.

    If the "default" argument specifies a file name,
    then the dialog box will start with that file.
    """
    if title:
        print(title)
    for line in msg.split("\n"):
        print(line)
    try:
        f = raw_input("File: ")
    except KeyboardInterrupt:
        f = None
    if not f: return None
    return os.path.normpath(f)


#-------------------------------------------------------------------
# filesavebox
#-------------------------------------------------------------------
def filesavebox(msg=None, title=None, default=None):
    """
    A file to get the name of a file to save.
    Returns the name of a file, or None if user chose to cancel.

    If the "default" argument specifies a file name,
    then the dialog box will start with that file.
    """
    if title:
        print(title)
    if msg:
        for line in msg.split("\n"):
            print(line)
    try:
        f = raw_input("File: ")
    except KeyboardInterrupt:
        f = None
    if not f: return None
    return os.path.normpath(f)

#-----------------------------------------------------------------------
#
# test/demo easygui
#
#-----------------------------------------------------------------------
def _test():
    # simple way to clear the console
    print "\n" * 100
    # START DEMONSTRATION DATA ===================================================
    choices_abc = ["This is choice 1", "And this is choice 2"]
    msg = "Pick one! This is a huge choice, and you've got to make the right one " \
        "or you will surely mess up the rest of your life, and the lives of your " \
        "friends and neighbors!"
    title = ""

    # ============================= define a code snippet =========================
    code_snippet = ("dafsdfa dasflkj pp[oadsij asdfp;ij asdfpjkop asdfpok asdfpok asdfpok"*3) +"\n"+\
"""# here is some dummy Python code
for someItem in myListOfStuff:
    do something(someItem)
    do something()
    do something()
    if somethingElse(someItem):
        doSomethingEvenMoreInteresting()

"""*16
    #======================== end of code snippet ==============================

    #================================= some text ===========================
    text_snippet = ((\
"""It was the best of times, and it was the worst of times.  The rich ate cake, and the poor had cake recommended to them, but wished only for enough cash to buy bread.  The time was ripe for revolution! """ \
*5)+"\n\n")*10

    #===========================end of text ================================

    intro_message = ("Pick the kind of box that you wish to demo.\n\n"
     + "In EasyGui, all GUI interactions are invoked by simple function calls.\n\n" +
    "EasyGui is different from other GUIs in that it is NOT event-driven.  It allows" +
    " you to program in a traditional linear fashion, and to put up dialogs for simple" +
    " input and output when you need to. If you are new to the event-driven paradigm" +
    " for GUIs, EasyGui will allow you to be productive with very basic tasks" +
    " immediately. Later, if you wish to make the transition to an event-driven GUI" +
    " paradigm, you can move to an event-driven style with a more powerful GUI package" +
    "such as anygui, PythonCard, Tkinter, wxPython, etc."
    + "\n\nEasyGui is running Tk version: " + "DUMMY PACKAGE"
    )

    #========================================== END DEMONSTRATION DATA


    while 1: # do forever
        choices = [
            "msgbox",
            "buttonbox",
            "buttonbox(image) -- an example of buttonbox with an 'image' specification",
            "choicebox",
            "multchoicebox",
            "textbox",
            "ynbox",
            "ccbox",
            "enterbox",
            "codebox",
            "integerbox",
            "boolbox",
            "indexbox",
            "filesavebox",
            "fileopenbox",
            "passwordbox",
            "multenterbox",
            "multpasswordbox",
            "diropenbox",
            "About EasyGui",
            " Help"
            ]
        choice = choicebox(msg=intro_message
            , title="EasyGui " + EasyGuiRevisionInfo
            , choices=choices)

        if not choice: return

        reply = choice.split()

        if   reply[0] == "msgbox":
            reply = msgbox("short msg", "This is a long title")
            print "Reply was:", repr(reply)

        elif reply[0] == "About":
            reply = abouteasygui()

        elif reply[0] == "Help":
            help("easygui")

        elif reply[0] == "buttonbox":
            reply = buttonbox()
            print "Reply was:", repr(reply)

            reply = buttonbox(msg=msg
            , title="Demo of Buttonbox with many, many buttons!"
            , choices=choices)
            print "Reply was:", repr(reply)

        elif reply[0] == "buttonbox(image)":
            image = "python_and_check_logo.gif"

            msg   = "Pretty nice, huh!"
            reply=msgbox(msg,image=image, ok_button="Wow!")
            print "Reply was:", repr(reply)

            msg   = "Do you like this picture?"
            choices = ["Yes","No","No opinion"]

            reply=buttonbox(msg,image=image,choices=choices)
            print "Reply was:", repr(reply)

            image = os.path.normpath("python_and_check_logo.png")
            reply=buttonbox(msg,image=image, choices=choices)
            print "Reply was:", repr(reply)

            image = os.path.normpath("zzzzz.gif")
            reply=buttonbox(msg,image=image, choices=choices)
            print "Reply was:", repr(reply)

        elif reply[0] == "boolbox":
            reply = boolbox()
            print "Reply was:", repr(reply)

        elif reply[0] == "enterbox":
            message = "Enter the name of your best friend."\
                      "\n(Result will be stripped.)"
            reply = enterbox(message, "Love!", "     Suzy Smith     ")
            print "Reply was:", repr(reply)

            message = "Enter the name of your best friend."\
                      "\n(Result will NOT be stripped.)"
            reply = enterbox(message, "Love!", "     Suzy Smith     ",strip=False)
            print "Reply was:", repr(reply)

            reply = enterbox("Enter the name of your worst enemy:", "Hate!")
            print "Reply was:", repr(reply)

        elif reply[0] == "integerbox":
            reply = integerbox(
                "Enter a number between 3 and 333",
                "Demo: integerbox WITH a default value",
                222, 3, 333)
            print "Reply was:", repr(reply)

            reply = integerbox(
                "Enter a number between 0 and 99",
                "Demo: integerbox WITHOUT a default value"
                )
            print "Reply was:", repr(reply)

        elif reply[0] == "diropenbox":
            title = "Demo of diropenbox"
            msg = "This is a test of the diropenbox.\n\nPick the directory that you wish to open."
            d = diropenbox(msg, title)
            print "You chose directory...:", d

        elif reply[0] == "fileopenbox":
            f = fileopenbox()
            print "You chose to open file:", f

        elif reply[0] == "filesavebox":
            f = filesavebox()
            print "You chose to save file:", f

        elif reply[0] == "indexbox":
            title = reply[0]
            msg   =  "Demo of " + reply[0]
            choices = ["Choice1", "Choice2", "Choice3", "Choice4"]
            reply = indexbox(msg, title, choices)
            print "Reply was:", repr(reply)

        elif reply[0] == "passwordbox":
            reply = passwordbox("Demo of password box WITHOUT default"
                + "\n\nEnter your secret password", "Member Logon")
            print "Reply was:", str(reply)

            reply = passwordbox("Demo of password box WITH default"
                + "\n\nEnter your secret password", "Member Logon", "alfie")
            print "Reply was:", str(reply)

        elif reply[0] == "multenterbox":
            msg = "Enter your personal information"
            title = "Credit Card Application"
            fieldNames = ["Name","Street Address","City","State","ZipCode"]
            fieldValues = []  # we start with blanks for the values
            fieldValues = multenterbox(msg,title, fieldNames)

            # make sure that none of the fields was left blank
            while 1:
                if fieldValues == None: break
                errmsg = ""
                for i in range(len(fieldNames)):
                    if fieldValues[i].strip() == "":
                        errmsg = errmsg + ('"%s" is a required field.\n\n' % fieldNames[i])
                if errmsg == "": break # no problems found
                fieldValues = multenterbox(errmsg, title, fieldNames, fieldValues)

            print "Reply was:", fieldValues

        elif reply[0] == "multpasswordbox":
            msg = "Enter logon information"
            title = "Demo of multpasswordbox"
            fieldNames = ["Server ID", "User ID", "Password"]
            fieldValues = []  # we start with blanks for the values
            fieldValues = multpasswordbox(msg,title, fieldNames)

            # make sure that none of the fields was left blank
            while 1:
                if fieldValues == None: break
                errmsg = ""
                for i in range(len(fieldNames)):
                    if fieldValues[i].strip() == "":
                        errmsg = errmsg + ('"%s" is a required field.\n\n' % fieldNames[i])
                if errmsg == "": break # no problems found
                fieldValues = multpasswordbox(errmsg, title, fieldNames, fieldValues)

            print "Reply was:", fieldValues


        elif reply[0] == "ynbox":
            reply = ynbox(msg, title)
            print "Reply was:", repr(reply)

        elif reply[0] == "ccbox":
            reply = ccbox(msg)
            print "Reply was:", repr(reply)

        elif reply[0] == "choicebox":
            longchoice = "This is an example of a very long option which you may or may not wish to choose."*2
            listChoices = ["nnn", "ddd", "eee", "fff", "aaa", longchoice
                    , "aaa", "bbb", "ccc", "ggg", "hhh", "iii", "jjj", "kkk", "LLL", "mmm" , "nnn", "ooo", "ppp", "qqq", "rrr", "sss", "ttt", "uuu", "vvv"]

            msg = "Pick something. " + ("A wrapable sentence of text ?! "*30) + "\nA separate line of text."*6
            reply = choicebox(msg=msg, choices=listChoices)
            print "Reply was:", repr(reply)

            msg = "Pick something. "
            reply = choicebox(msg=msg, choices=listChoices)
            print "Reply was:", repr(reply)

            msg = "Pick something. "
            reply = choicebox(msg="The list of choices is empty!", choices=[])
            print "Reply was:", repr(reply)

        elif reply[0] == "multchoicebox":
            listChoices = ["aaa", "bbb", "ccc", "ggg", "hhh", "iii", "jjj", "kkk"
                , "LLL", "mmm" , "nnn", "ooo", "ppp", "qqq"
                , "rrr", "sss", "ttt", "uuu", "vvv"]

            msg = "Pick as many choices as you wish."
            reply = multchoicebox(msg,"DEMO OF multchoicebox", listChoices)
            print "Reply was:", repr(reply)

        elif reply[0] == "textbox":
            msg = "Here is some sample text. " * 16
            reply = textbox(msg, "Text Sample", text_snippet)
            print "Reply was:", repr(reply)

        elif reply[0] == "codebox":
            msg = "Here is some sample code. " * 16
            reply = codebox(msg, "Code Sample", code_snippet)
            print "Reply was:", repr(reply)

        else:
            msgbox("Choice\n\n" + choice + "\n\nis not recognized", "Program Logic Error")
            return

EASYGUI_ABOUT_INFORMATION = '''
========================================================================
version 0.83 2008-06-12
========================================================================

BUG FIXES
------------------------------------------------------
 * fixed a bug in which fileopenbox, filesavebox, and diropenbox
   were returning an empty tuple, rather than None, when a user
   cancelled.  Thanks to Nate Soares for reporting this and sending
   in a fix.

BACKWARD-INCOMPATIBLE CHANGES
------------------------------------------------------
 * changed enterbox so that by default it strips its result
   (i.e. removes leading and trailing whitespace).
   If you want it not to strip, use keyword argument:  strip=False.

   This change makes it easier to test the results of the call::

        reply = enterbox(....)
        if reply:
            ...
        else:
            ...

 * changed the name of the "button_text" (formerly "buttonMessage") parameter
   to "ok_button" in the msgbox parameters.

========================================================================
version 0.80 2008-06-02
========================================================================

ENHANCEMENTS
------------------------------------------------------
 * added image keyword to msgbox and buttonbox
   Note that it can display only .gif images.
   see: http://effbot.org/tkinterbook/photoimage.htm
 * improved a lot of the docstrings.
 * added a new abouteasygui() function

BUG FIXES
------------------------------------------------------
 * changed mutable default arguments (lists) to tuples

 * diropenbox, fileopenbox, and filesavebox now execute
   os.path.normpath() on the choice before returning it.
   This fixes a nasty bug/inconvenience for Windows users.

 * In integerbox:
   old behavior: If user cancels, the default value is returned.
   new behavior: If user cancels, None is returned.

   NOTE that this bugfix has the potential to break existing programs.


CHANGES
------------------------------------------------------
 * removed the "restore default" button on enterbox.
   It was non-standard and was too long to display properly in
   some environments.
 * default message for buttonbox changed from
   "Shall I continue?" to just "".

BACKWARD-INCOMPATIBLE CHANGES
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   These changes may break backward compatibility.

   Note that the following changes may break backward compatibility
   in programs that invoke EasyGui functions with keyword
   (rather than positional) arguments.

   They have been changed in order to standardize keyword arguments, so
   that EasyGui functions can be more easily used with keyword arguments.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
changed parameter name "message"              to "msg" everywhere
changed parameter name "buttonMessage"        to "button_text"
changed parameter name "argListOfFieldNames"  to "fields"
changed parameter name "argListOfFieldValues" to "values"

changed the following parameter names  to "default":
    argDefault
    argDefaultPassword
    argDefaultText
    argInitialFile
    argInitialDir
'''

def abouteasygui():
    """
    shows the easygui revision history
    """
    codebox("About EasyGui\n"+EasyGuiRevisionInfo,"EasyGui",EASYGUI_ABOUT_INFORMATION)
    return None

if __name__ == '__main__':
    _test()
