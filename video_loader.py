"""
Use a video library to get, edit, and save video.

The api for this library is as follows.

Video(source)
    
"""
# TODO
# Add the meanings of various return codes.

import os
# Get whatever library is avalible.

# Build first for ffmpeg. Then, if that fails. Build for cv2.
# For now, I know how to make cv2 work, so load that.

# import ffmepg
try:
    import cv2
except ImportError:
    cv2 = None
else:
    class Video():
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
        def get_frame_count(self):
            """Get the number of frames that have passed."""
            return self.cap.get(cv2.CAP_PROP_POS_FRAMES)

        def set_frame_count(self, frame_count):
            """Set the number of frames that have passed.
               Returns a status code."""
            # Add status meaning.
            return self.cap.set(cv2.CAP_PROP_POS_FRAMES)

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
            return self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)

        #Height of the frames in the video stream.
        def get_frame_height(self):
            """Get the height of the frames."""
            return self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

        #Frame rate. Frames Per Second
        def get_fps(self):
            """Get the frames per second speed of the video."""
            return self.cap.get(cv2.CAP_PROP_FPS)

        #Number of frames in the video file.
        def get_frame_count(self):
            """Get the number of frames in the video file."""
            return self.cap.get(cv2.CAP_PROP_FRAME_COUNT)

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

if __name__ == '__main__':
    test()
