import mappersession as session
import libmapper as mpr
import json
import os

# An end-to-end test case for saving, loading and clearing sessions
if __name__ == '__main__':
    g = mpr.Graph()
    g.poll(100)

    # Load a test session
    session.load_file("test_session.json")

    # Wait a few seconds for graph to update
    g.poll(2000)

    # Save the session
    session.save("test_session_saved.json", "A simple test session")

    # Check that the session files are identical
    og_file = open("test_session.json")
    saved_file = open("test_session_saved.json")
    og_data = json.load(og_file)
    saved_data = json.load(saved_file)
    saved_file.close()

    if (og_data != saved_data):
        print("Failed: saved session not equal to loaded session...")
        print("Original session: ", og_data)
        print("Saved session: ", saved_data)
    
    # Delete the saved session file
    os.remove("test_session_saved.json")

    print("Test complete")