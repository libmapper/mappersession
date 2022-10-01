import sys
import argparse
import jsonschema
from jsonschema import validate
import libmapper as mpr

def main():
    # Parse arguments
    parser = createParser()
    args = parser.parse_args()
    if (args.save is not None):
        save(args.save, args.description, {})
    elif (args.load is not None):
        load(args.load)
    else:
        print("Not enough arguments provided, please use --save or --load with JSON file path(s)")
        return

def save(file, description, viewName="", views={}):
    """saves the current mapping state as a JSON session file.
    
    :param file: The JSON file to save the session into 
    :param description: A short description of the current session
    :param viewName: Name of the GUI that's adding metadata
    :param views: GUI related object for recreating the session
    :return: The session JSON object
    """

    # Create JSON from network state following the schema
    session = {}
    session.fileversion = "2.3"
    session.description = description
    session.views = views

    # Populate maps
    session.maps = []

    # Add unmapped destination signal values
    session.destinationValues = []

    # Save into the file
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(session, f, ensure_ascii=False, indent=4)

def load(files):
    """loads one or more sessions with options for staging and cycling.
    
    :param files: The JSON files to load
    :return: None
    """
    return

def createParser():
    parser = argparse.ArgumentParser(description="Save or load a mapping session")
    parser.add_argument(
        '--load', type=argparse.FileType('r'), nargs='+',
        metavar='PATH',
        help="Session JSON file(s) to load")
    parser.add_argument(
        '--save', type=argparse.FileType('w'),
        metavar='PATH',
        help="Save session as JSON file")
    parser.add_argument(
        '--description', "-d", type=ascii,
        help="Description of session, used when saving")
    # TODO:
    # Overwrite save file
    # 
    return parser

if __name__ == "__main__":
    main()