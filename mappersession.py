import sys
import argparse
import libmapper as mpr

def main():
    # Parse arguments
    parser = createParser()
    args = parser.parse_args()
    if (args.save is not None):
        saveSession(args.save)
    elif (args.load is not None):
        loadSession(args.load)
    else:
        print("Not enough arguments provided, please use --save or --load with JSON file path(s)")
        return

def saveSession(file):
    # Create JSON from network state
    

def loadSession(files):
    # Load the first session in 'files' and store the rest for possible session changes
    

def createParser():
    parser = argparse.ArgumentParser(description="Save or load a mapping session")
    parser.add_argument(
        '--load', type=argparse.FileType('r'), nargs='+',
        metavar='PATH',
        help="Session JSON file(s) to load (default: standard input).")
    parser.add_argument(
        '--save', type=argparse.FileType('w'),
        metavar='PATH',
        help="Save session as JSON file (default: standard output)")
    return parser

if __name__ == "__main__":
    main()