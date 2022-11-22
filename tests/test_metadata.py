import libmapper as mpr
import os

# An end-to-end test case for saving, loading and clearing sessions
if __name__ == '__main__':
    dev = mpr.Device("DummyDevice")

    sig1 = dev.add_signal(mpr.Direction.INCOMING, "velocity_3d", 3,
                        mpr.Type.FLOAT, "m/s", -9.9, 9.9, None)
    sig2 = dev.add_signal(mpr.Direction.OUTGOING, "rgb_brightness", 3,
                        mpr.Type.INT32, "lumens", 0, 255, None)
    sig2.reserve_instances(4)
    
    while(True):
        dev.poll(100)