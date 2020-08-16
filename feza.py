# import the necessary packages
from __future__ import division
from picamera.array import PiRGBArray
from picamera import PiCamera
import threading
import time
import cv2
import socket
import struct
import math
# initialize the camera and grab a reference to the raw camera capture

command_ip = ''
command_port = 5005

class FrameSegment(object):
    """ 
    Object to break down image frame segment
    if the size of image exceed maximum datagram size 
    """
    MAX_DGRAM = 2**16
    MAX_IMAGE_DGRAM = MAX_DGRAM - 64  # extract 64 bytes in case UDP frame overflown

    def __init__(self, sock, port, addr="192.168.1.107"):
        self.s = sock
        self.port = port
        self.addr = addr

    def udp_frame(self, img):
        """ 
        Compress image and Break down
        into data segments 
        """
        compress_img = cv2.imencode('.jpg', img)[1]
        dat = compress_img.tostring()
        size = len(dat)
        count = math.ceil(size/(self.MAX_IMAGE_DGRAM))
        array_pos_start = 0
        while count:
            array_pos_end = min(size, array_pos_start + self.MAX_IMAGE_DGRAM)
            self.s.sendto(struct.pack("B", count) +
                          dat[array_pos_start:array_pos_end],
                          (self.addr, self.port)
                          )
            array_pos_start = array_pos_end
            count -= 1


def main():
    camera = PiCamera()
    camera.resolution = (320,240)
    camera.framerate = 32
    rawCapture = PiRGBArray(camera, size=(320,240))
    # allow the camera to warmup

    listenerThread = threading.Thread(target=udpListener)
    listenerThread.setDaemon(True)
    listenerThread.start()

    port = 12345
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    fs = FrameSegment(sock, port)

    time.sleep(0.1)
    # capture frames from the camera
    for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        # grab the raw NumPy array representing the image, then initialize the timestamp
        # and occupied/unoccupied text
        image = frame.array
        # show the frame
        fs.udp_frame(image)
        cv2.imshow("Frame", image)
        key = cv2.waitKey(1) & 0xFF
        # clear the stream in preparation for the next frame
        rawCapture.truncate(0)
        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break

def udpListener():
    print("udp listener thread started")
    comsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    comsock.bind((command_ip, command_port))
    while True:
        data, addr = comsock.recvfrom(1024)
        print("command: %s" % str(data, 'utf-8'))

if __name__ == "__main__":
    main()
