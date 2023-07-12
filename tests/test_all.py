import libmapper as mpr
import json
import os
import sys

try:
    import mappersession as session
except:
    try:
        sys.path.append(
                        os.path.join(os.path.join(os.getcwd(),
                                                  os.path.dirname(sys.argv[0])),
                                     '../src/mappersession'))
        import mappersession as session
    except:
        print('Error importing mappersession module.')
        sys.exit(1)

# An end-to-end test case for saving, loading and clearing sessions
if __name__ == '__main__':
    graph = mpr.Graph()
    graph.poll(100)

    # Load a test session
    session.load("test_session.json", graph=graph)

    # Wait a few seconds for graph to update
    graph.poll(2000)

    # Save the session
    session.save("test_session_saved.json", "A simple test session", graph=graph)

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

    graph.free()
