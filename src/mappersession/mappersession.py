import sys
import json
import jsonschema
import libmapper as mpr
from jsonschema import validate

g = mpr.Graph()

def save(filename, description="", values=[], viewName="", views=[]):
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
        newMap["process_loc"] = mpr.Location(g.maps()[mapIdx][mpr.Property.PROCESS_LOCATION]).name
        newMap["protocol"] = g.maps()[mapIdx][mpr.Property.PROTOCOL].name
        newMap["scope"] = []
        scopeDevs = g.maps()[mapIdx][mpr.Property.SCOPE]
        for devIdx in range(len(scopeDevs)):
            newMap["scope"].append(scopeDevs[devIdx][mpr.Property.NAME])
        newMap["use_inst"] = g.maps()[mapIdx][mpr.Property.USE_INSTANCES]
        newMap["version"] = g.maps()[mapIdx][mpr.Property.VERSION]

        # Add to maps
        session["maps"].append(newMap)

    # Save into the file\
    if filename != "":
        with open(filename.strip("'"), 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=4)
            print("Saved session as: " + filename)
    return session
    

def load(files, should_stage=False, should_clear=True):
    """loads one or more sessions with options for staging and cycling.
    
    :param files (List): The JSON files to load
    :optional param should_stage (Boolean): Manages continuous staging and reconnecting of missing devices and signals as they appear, default false
    :optional param should_clear (Boolean): Clear all maps before loading the session, default True
    :return (Dict): visual session information relevant to GUIs
    """

    # TODO: multiple files at once

    global g

    # Parse session file
    if len(files) == 0:
        print("No session files provided, please supply at least one session .json file")
        return
    file = open(files[0].name)
    data = json.load(file)

    # Validate session according to schema
    schema = json.load(open("mappingSessionSchema.json"))
    validate(instance=data, schema=schema)

    # Keep list of staged maps
    connected_maps = []
    staged_maps = data["maps"]

    # Clear current session if requested
    if should_clear:
        clear()

    should_run = True
    while should_run:
        # Confirm all connected maps are actually connected
        for connected_map in connected_maps:
            found_map = find_map(connected_map["sources"], connected_map["destinations"][0])
            if not found_map:
                print("map re-staged: ", connected_map["sources"], "->", connected_map["destinations"])
                staged_maps.append(connected_map.copy())
                connected_maps.remove(connected_map)

        # Create all maps that aren't present in the session yet
        for staged_map in staged_maps:
            # Check if the map's signals are available
            srcs = [find_sig(k) for k in staged_map["sources"]]
            dst = find_sig(staged_map["destinations"][0])
            if all(srcs) and dst:
                # Create map and remove from staged list
                new_map = mpr.Map(srcs, dst)
                if not new_map:
                    print('error: failed to create map', staged_map["sources"], "->", staged_map["destinations"])
                    continue
                print('created map: ', staged_map["sources"], "->", staged_map["destinations"])
                # Set map properties
                new_map[mpr.Property.EXPRESSION] = staged_map["expression"]
                new_map[mpr.Property.MUTED] = staged_map["muted"]
                if staged_map["process_loc"] == 'SOURCE':
                    new_map[mpr.Property.PROCESS_LOCATION] = mpr.Location.SOURCE
                elif staged_map["process_loc"] == 'DESTINATION':
                    new_map[mpr.Property.PROCESS_LOCATION] = mpr.Location.DESTINATION
                new_map[mpr.Property.PROCESS_LOCATION] = staged_map["process_loc"]
                if staged_map["protocol"] == 'udp' or staged_map["protocol"] == 'UDP':
                    new_map[mpr.Property.PROTOCOL] = mpr.Protocol.UDP
                elif staged_map["protocol"] == 'tcp' or staged_map["protocol"] == 'TCP':
                    new_map[mpr.Property.PROTOCOL] = mpr.Protocol.TCP
                # new_map[mpr.Property.SCOPE] = staged_map["scope"]
                new_map[mpr.Property.USE_INSTANCES] = staged_map["use_inst"]
                new_map[mpr.Property.VERSION] = staged_map["version"]
                # Push to network
                new_map.push()
                connected_maps.append(staged_map.copy())
                staged_maps.remove(staged_map)

        should_run = should_stage
        g.poll(1000) # Wait for one second before doing checks again

    return data["views"]

def clear():
    global g
    g.poll(50)
    for map in g.maps():
        map.release()
        map.push()
    g.poll(50)

def get_views(file, view_name):
    """retrieves view-related GUI parameters from a session json file
    
    :param file (String): The JSON file path to get the views from
    :param view_name (String): Name of the target view
    :return (Dict): visual session information relevant to GUIs, None if not found
    """
    schema = json.load(open("mappingSessionSchema.json"))
    data = json.load(open(file))
    validate(instance=data, schema=schema)
    for view in data["views"]:
        if view["name"] == view_name:
            return view["data"]
    return None

def find_sig(fullname):
    global g
    names = fullname.split('/', 1)
    dev = g.devices().filter(mpr.Property.NAME, names[0])
    if dev:
        sig = dev.next().signals().filter(mpr.Property.NAME, names[1])
        if not sig:
            return None
        return sig.next()
    else:
        return None

def find_map(srckeys, dstkey):
    srcs = [find_sig(k) for k in srckeys]
    dst = find_sig(dstkey)
    if not (all(srcs) and dst):
        return None
    intersect = dst.maps()
    for s in srcs:
        intersect = intersect.intersect(s.maps())
    for m in intersect:
        match = True
        match = match and (m.index(dst) >= 0)
        if match:
            for s in srcs:
                match = match and (m.index(s) >= 0)
        if match:
            return m
    return None