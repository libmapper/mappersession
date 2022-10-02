import sys
import argparse
import json
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

def save(filename, description, viewName="", views={}):
    """saves the current mapping state as a JSON session file.
    
    :param file: The JSON file to save the session into 
    :param description: A short description of the current session
    :param viewName: Name of the GUI that's adding metadata
    :param views: GUI related object for recreating the session
    :return: The session JSON object
    """

    # Create JSON from network state following the schema
    session = {}
    session["fileversion"] = "2.3"
    session["description"] = description.strip("'")
    session["views"] = views

    # Populate maps
    g = mpr.Graph()
    print("Collecting session state from network...")
    g.poll(1000)
    session["maps"] = []
    for mapIdx in range(len(g.maps())):
        newMap = {}
        # Source signals
        srcSigs = g.maps()[mapIdx].signals(mpr.Location.SOURCE)
        newMap["sources"] = []
        for srcIdx in range(len(srcSigs)):
            srcName = (srcSigs[srcIdx].device().get_property(mpr.Property.NAME) +
                        "/" + srcSigs[srcIdx].get_property(mpr.Property.NAME))
            newMap["sources"].append(srcName)
        # Destination signals
        dstSigs = g.maps()[mapIdx].signals(mpr.Location.DESTINATION)
        newMap["destinations"] = []
        for dstIdx in range(len(dstSigs)):
            dstName = (dstSigs[dstIdx].device().get_property(mpr.Property.NAME) +
                        "/" + dstSigs[dstIdx].get_property(mpr.Property.NAME))
            newMap["destinations"].append(dstName)

        # Other properties
        newMap["expression"] = g.maps()[mapIdx].get_property(mpr.Property.EXPRESSION)
        newMap["muted"] = g.maps()[mapIdx].get_property(mpr.Property.MUTED)
        newMap["process_loc"] = g.maps()[mapIdx].get_property(mpr.Property.PROCESS_LOCATION)
        #newMap["protocol"] = g.maps()[mapIdx].get_property(mpr.Property.PROTOCOL)
        #newMap["scope"] = g.maps()[mapIdx].get_property(mpr.Property.SCOPE)
        newMap["use_inst"] = g.maps()[mapIdx].get_property(mpr.Property.USE_INSTANCES)
        newMap["version"] = g.maps()[mapIdx].get_property(mpr.Property.VERSION)
        # Add to maps
        session["maps"].append(newMap)

    print(g.maps()[0].get_property(mpr.Property.EXPRESSION))
    

    # Add unmapped destination signal values
    session["destinationValues"] = []

    # Save into the file
    with open(filename.strip("'"), 'w', encoding='utf-8') as f:
        json.dump(session, f, ensure_ascii=False, indent=4)
    print("Saved session as: " + filename)

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
        '--save', type=ascii,
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