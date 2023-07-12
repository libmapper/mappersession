import os, sys

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

    # Load a series of legacy files
    session.load("legacy_2-0.json")
    session.load("legacy_2-1.json")
    session.load("legacy_2-2.json")
    session.load("legacy_2-3.json")

    print("Test complete")
