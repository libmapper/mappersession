import libmapper as mpr
import os, signal

done = False

def handler_done(signum, frame):
    global done
    print('signal received, quitting...')
    done = True

# An end-to-end test case for saving, loading and clearing sessions
if __name__ == '__main__':
    signal.signal(signal.SIGINT, handler_done)
    signal.signal(signal.SIGTERM, handler_done)

    dev1 = mpr.Device("dev1")
    sig2 = dev1.add_signal(mpr.Direction.OUTGOING, "out1", 3,
                           mpr.Type.INT32, "lumens", 0, 255, None)

    dev2 = mpr.Device("dev2")
    sig1 = dev2.add_signal(mpr.Direction.INCOMING, "drywet", 3,
                           mpr.Type.FLOAT, "m/s", -9.9, 9.9, None)
    
    while(not done):
        dev1.poll(100)
        dev2.poll(100)

    dev1.free()
    dev2.free()
