import mappersession as session
import os

# An end-to-end test case for saving, loading and clearing sessions
if __name__ == '__main__':

    # Load a series of legacy files
    session.load_file("legacy_2-0.json")
    session.load_file("legacy_2-1.json")
    session.load_file("legacy_2-2.json")
    session.load_file("legacy_2-3.json")

    print("Test complete")