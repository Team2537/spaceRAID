"""
Use a video library to get, edit, and save video.

The api for this library is as follows.

Video(source)
    
"""
__author__ = "Matthew Schweiss"
__version__ = "0.5"
# TODO
# Add the meanings of various return codes.
# Implement complete ffmpeg support.
__all__ = ["Video"]

import os
# Get whatever library is avalible.

# Build first for ffmpeg. Then, if that fails. Build for cv2.
# For now, I know how to make cv2 work, so load that.

# import ffmepg
try:
    import cv2
except ImportError:
    cv2 = None
    import ffmpeg # Errors if neither cv2 or ffmpeg is installed.
else:
    try:
        import ffmpeg
    except ImportError:
        ffmpeg = None
    
if cv2:
    def load_image(source):
        """Load the image from file."""
        return cv2.imread(os.path.abspath(source))

    def save_image(image, destination):
        """Save the image to a file."""
        return cv2.imwrite(os.path.abspath(source), image)
    
    class Video():

        __all__ = ['close', 'closed',   'get_fps',          'get_frame',
                   'get_frame_index',   'get_frame_height', 'get_frame_width',
                   'get_progress',      'get_timestamp',    'name', 'path',
                   'set_frame_index',   'set_progress',     'set_timestamp'
                   'get_frame_count']
        def __init__(self, source):
            self.name = os.path.basename(source)
            self.path = source
            self.cap = cv2.VideoCapture(os.path.abspath(source))

        #Current position of the video file in
        # milliseconds or video capture timestamp.
        def get_timestamp(self):
            """Get the position in the video in milliseconds."""
            return self.cap.get(cv2.CAP_PROP_POS_MSEC)

        def set_timestamp(self, timestamp):
            """Set the position in the video in milliseconds.
               Returns a status code."""
            # Add status meaning.
            return self.cap.set(cv2.CAP_PROP_POS_MSEC, timestamp)

        #0-based index of the frame to be decoded/captured next.
        def get_frame_index(self):
            """Get the number of frames that have passed."""
            return self.cap.get(cv2.CAP_PROP_POS_FRAMES)

        def set_frame_index(self, frame_count):
            """Set the number of frames that have passed.
               Returns a status code."""
            # Add status meaning.
            if frame_count < 0:
                frame_count = 0
            return self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)

        #Relative position of the video file:
        #0 - start of the film, 1 - end of the film.
        def get_progress(self):
            """Get the percentage that is passed (0 to 1)."""
            return self.cap.get(cv2.CAP_PROP_POS_AVI_RATIO)

        def set_progress(self, progress):
            """Set the percentage that is passed (0 to 1).
               Returns a status code."""
            # Add status meaning.
            return self.cap.set(cv2.CAP_PROP_POS_AVI_RATIO, progress)

        #Width of the frames in the video stream.
        def get_frame_width(self):
            """Get the width of the frames."""
            # Change to an integer as it should be.
            return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

        #Height of the frames in the video stream.
        def get_frame_height(self):
            """Get the height of the frames."""
            # Change to an integer as it should be.
            return int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        #Frame rate. Frames Per Second
        def get_fps(self):
            """Get the frames per second speed of the video."""
            return self.cap.get(cv2.CAP_PROP_FPS)

        #Number of frames in the video file.
        def get_frame_count(self):
            """Get the number of frames in the video file."""
            # passed as a float but has no buisness being a float.
            return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Codes that I did not include.

        # More complicated than I need.
        cv2.CAP_PROP_FOURCC         #4-character code of codec.
        cv2.CAP_PROP_CONVERT_RGB    #Boolean flags indicating whether images should be converted to RGB.
        cv2.CAP_PROP_FORMAT         #Format of the Mat objects returned by retrieve().

        
        cv2.CAP_PROP_MODE           #Backend-specific value indicating the current capture mode.
        # Camera settings only.
        cv2.CAP_PROP_BRIGHTNESS     #Brightness of the image (only for cameras).
        cv2.CAP_PROP_CONTRAST       #Contrast of the image (only for cameras).
        cv2.CAP_PROP_SATURATION     #Saturation of the image (only for cameras).
        cv2.CAP_PROP_HUE            #Hue of the image (only for cameras).
        cv2.CAP_PROP_GAIN           #Gain of the image (only for cameras).
        cv2.CAP_PROP_EXPOSURE       #Exposure (only for cameras).

        # Only supported the DC1394 v 2.x backend
        # These first two don't seem present. That is why they are commented out.
        #cv2.CAP_PROP_WHITE_BALANCE_U #The U value of the whitebalance setting (note: only supported by DC1394 v 2.x backend currently)
        #cv2.CAP_PROP_WHITE_BALANCE_V #The V value of the whitebalance setting (note: only supported by DC1394 v 2.x backend currently)
        cv2.CAP_PROP_RECTIFICATION  #Rectification flag for stereo cameras (note: only supported by DC1394 v 2.x backend currently)
        cv2.CAP_PROP_ISO_SPEED      #The ISO speed of the camera (note: only supported by DC1394 v 2.x backend currently)
        cv2.CAP_PROP_BUFFERSIZE     #Amount of frames stored in internal buffer memory (note: only supported by DC1394 v 2.x backend currently)

        def get_frame(self):
            """Read the next line from the file."""
            ret, frame = self.cap.read()
            if ret:
                return frame
            return None

        def closed(self):
            """Return if the video file is closed."""
            return not self.cap.isOpened()

        def close(self):
            """Close the file and release the resources."""
            self.cap.release()

    def test():
        video = Video('Examples/Saturday 3-11-17_ND.mp4')
        print("Width: %s\tHeight:\t%s" % (video.get_frame_width(),
                                          video.get_frame_height()))

        try:
            while not video.closed():
                frame = video.get_frame()

                if frame is not None:
                    cv2.imshow('Video', frame)
                else:
                    break
                    
                if cv2.waitKey(1) & 0xFF == ord('q'):
                     break
        finally:
            video.close()
            cv2.destroyAllWindows()
            
else: # elif ffmpeg:    
    # For ffmpeg compatability it should be possible to use the code found at
    # https://github.com/Zulko/moviepy/blob/master/moviepy/video/io/ffmpeg_reader.py
    # https://github.com/dschreij/opensesame-plugin-media_player_mpy/

    # These should be enough to make everything work with ffmpeg, though not well.
    # That said. I am not taking the time now to build the ffmpeg support out.
    # Also, look the libraries opensesame-plugin-media_player_mpy, mediadecoder,
    # and moviepy
    class Video():
        raise NotImplementedError("This has not been build yet.")

if __name__ == '__main__':
    test()
