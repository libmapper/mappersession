import sys
import argparse
import json
import jsonschema
import libmapper as mpr
from jsonschema import validate

def main():
    # Parse arguments
    parser = createParser()
    args = parser.parse_args()
    if (args.save is not None):
        save(args.save, args.description if args.description != None else "")
    elif (args.load is not None):
        load(args.load, args.clear if args.clear != None else True)
    else:
        print("Not enough arguments provided, please use --save or --load with JSON file path(s)")
        return

def save(filename, description="", values=[], viewName="", views={}):
    """saves the current mapping state as a JSON session file.
    
    :param file: The JSON file to save the session into 
    :param description: A short description of the current session
    :optional param values: Array of {name, value} pairs for signals to set on session load
    :optional param viewName: Name of the GUI that's adding metadata
    :optional param views: GUI related object for recreating the session
    :return: The session JSON object
    """

    # Create JSON from network state following the schema
    session = {}
    session["fileversion"] = "2.3"
    session["description"] = description.strip("'")
    session["values"] = values
    session["views"] = views

    # Populate maps
    g = mpr.Graph()
    print("Collecting maps from network...")
    g.poll(1000)
    session["maps"] = []
    for mapIdx in range(len(g.maps())):
        newMap = {}
        # Source signals
        srcSigs = g.maps()[mapIdx].signals(mpr.Location.SOURCE)
        newMap["sources"] = []
        for srcIdx in range(len(srcSigs)):
            srcName = (srcSigs[srcIdx].device()[mpr.Property.NAME] +
                        "/" + srcSigs[srcIdx][mpr.Property.NAME])
            newMap["sources"].append(srcName)
        # Destination signals
        dstSigs = g.maps()[mapIdx].signals(mpr.Location.DESTINATION)
        newMap["destinations"] = []
        for dstIdx in range(len(dstSigs)):
            dstName = (dstSigs[dstIdx].device()[mpr.Property.NAME] +
                        "/" + dstSigs[dstIdx][mpr.Property.NAME])
            newMap["destinations"].append(dstName)

        # Other properties
        newMap["expression"] = g.maps()[mapIdx][mpr.Property.EXPRESSION]
        newMap["muted"] = g.maps()[mapIdx][mpr.Property.MUTED]
        newMap["process_loc"] = g.maps()[mapIdx][mpr.Property.PROCESS_LOCATION]
        newMap["protocol"] = g.maps()[mapIdx][mpr.Property.PROTOCOL].name
        newMap["scope"] = []
        scopeDevs = g.maps()[mapIdx][mpr.Property.SCOPE]
        for devIdx in range(len(scopeDevs)):
            newMap["scope"].append(scopeDevs[devIdx][mpr.Property.NAME])
        newMap["use_inst"] = g.maps()[mapIdx][mpr.Property.USE_INSTANCES]
        newMap["version"] = g.maps()[mapIdx][mpr.Property.VERSION]

        # Add to maps
        session["maps"].append(newMap)

    # Save into the file
    with open(filename.strip("'"), 'w', encoding='utf-8') as f:
        json.dump(session, f, ensure_ascii=False, indent=4)
    print("Saved session as: " + filename)

def load(files, stage=False, clear=True):
    """loads one or more sessions with options for staging and cycling.
    
    :param files (List): The JSON files to load
    :optional param stage (Boolean): Manages continuous staging and reconnecting of missing devices and signals as they appear, default false
    :optional param clear (Boolean): Clear all maps before loading the session, default True
    :return (Dict): visual session information relevant to GUIs
    """

    # Parse session file and prepare flags
    g = mpr.Graph()
    connected_maps = []
    staged_maps = []


    # Clear current session if requested
    if clear:
        pass

    should_run = True
    while should_run:
        # Create all maps that aren't present in the session yet

        should_run = stage
        g.poll(1000) # Wait for one second before doing checks again

    # Retrieve views from session file
    views = []

    return views

def createParser():
    parser = argparse.ArgumentParser(description="Save or load a mapping session")
    parser.add_argument(
        '--load', type=argparse.FileType('r'), nargs='+',
        metavar='PATH',
        help="Session JSON file(s) to load")
    parser.add_argument(
        '--clear', action=argparse.BooleanOptionalAction,
        help="Set if maps should be cleared during session load, or --no-clear to leave maps")
    parser.add_argument(
        '--save', type=ascii,
        metavar='PATH',
        help="Save session as JSON file")
    parser.add_argument(
        '--description', type=ascii,
        help="Description of session, used when saving")
    # TODO:
    # Overwrite save file
    # 
    return parser

if __name__ == "__main__":
    main()