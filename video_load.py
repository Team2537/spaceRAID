"""
Use a video library to get, edit, and save video.

The api for this library is as follows.

Video(source)
    
"""
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
        def __init__(source):
            self.source = cv2.
