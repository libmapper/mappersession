import sys
import platform
import json
import jsonschema
import libmapper as mpr
from jsonschema import validate
import pkgutil
import threading
if platform.system() == 'Windows':
    import msvcrt
else:
    import select

g = mpr.Graph()
staging_thread = None
kill_staging = False
# Bookkeeping for maps
connected_maps = []
staged_maps = []
# Session cycling files
cur_session_idx = 0
session_cycling_filenames = []

def save(filename="", description="", values=[], view_name="", views=[]):
    """saves the current mapping state as a JSON session file.
    
    :optional param filename (String): The JSON file to save the session into
    :optional param description (String): A short description of the current session
    :optional param values (List): Array of signal {name, value} pairs to set on session load
    :optional param view_name (String): Name of the GUI that's adding metadata
    :optional param views (List): GUI related object for recreating the session
    :return (Dict): The session JSON object
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

# Internal staging method to be used in a thread
# maps that should be staged should be added to the global 'staged_maps'
def stage():
    global kill_staging, staged_maps, connected_maps
    kill_staging = False
    print("Starting session staging")
    while True:
        if kill_staging:
            print("Ending session staging")
            break
        else:
            g.poll(100)
            # Re-stage any missing "connected" maps
            for connected_map in connected_maps:
                found_map = find_map(connected_map["sources"], connected_map["destinations"][0])
                if not found_map:
                    print("map re-staged: ", connected_map["sources"], "->", connected_map["destinations"])
                    staged_maps.append(connected_map.copy())
                    connected_maps.remove(connected_map)
            # Try to create any staged maps that we can
            try:
                new_maps = try_make_maps(staged_maps)
                for new_map in new_maps:
                    connected_maps.append(new_map.copy())
                    staged_maps.remove(new_map)
            except:
                pass

# Attempts to create any eligible maps that have all sources and destination present 
def try_make_maps(maps):
    new_maps = []
    for map in maps:
        # Check if the map's signals are available
        srcs = [find_sig(k) for k in map["sources"]]
        dst = find_sig(map["destinations"][0])
        if all(srcs) and dst:
            # Create map and remove from staged list
            new_map = mpr.Map(srcs, dst)
            if not new_map:
                print('error: failed to create map', map["sources"], "->", map["destinations"])
                continue
            print('created map: ', map["sources"], "->", map["destinations"])
            # Set map properties
            new_map[mpr.Property.EXPRESSION] = map["expression"]
            new_map[mpr.Property.MUTED] = map["muted"]
            if map["process_loc"] == 'SOURCE':
                new_map[mpr.Property.PROCESS_LOCATION] = mpr.Location.SOURCE
            elif map["process_loc"] == 'DESTINATION':
                new_map[mpr.Property.PROCESS_LOCATION] = mpr.Location.DESTINATION
            new_map[mpr.Property.PROCESS_LOCATION] = map["process_loc"]
            if map["protocol"] == 'udp' or map["protocol"] == 'UDP':
                new_map[mpr.Property.PROTOCOL] = mpr.Protocol.UDP
            elif map["protocol"] == 'tcp' or map["protocol"] == 'TCP':
                new_map[mpr.Property.PROTOCOL] = mpr.Protocol.TCP
            # new_map[mpr.Property.SCOPE] = map["scope"]
            new_map[mpr.Property.USE_INSTANCES] = map["use_inst"]
            new_map[mpr.Property.VERSION] = map["version"]
            # Push to network
            new_map.push()
            new_maps.append(map.copy())
    return new_maps

def cycle_files(filenames):
    """manages cycling through multiple session files. A libmapper signal is created
    that changes which session is currently active, or users can use the left/right
    arrow keys to change sessions.
    
    :param filenames (String): The JSON files to load (1st is loaded immediately)
    :return (None): Blocks while executing, should CTL+C or hit 'e' to exit
    """

    global session_cycling_filenames, cur_session_idx

    cur_session_idx = 0
    session_cycling_filenames = filenames

    # Load first session file
    load_file(filenames[0], True)

    # Set up libmapper signal that controls the current session index
    dev = mpr.Device("mappersession")
    sig_cur_session = dev.add_signal(mpr.Direction.INCOMING, "cur_session_idx", 1,
                        mpr.Type.INT32, "", 0, len(filenames), None, cur_session_handler)

    while (True):
        dev.poll(50)

def cur_session_handler(sig, event, id, val, timetag):
    global session_cycling_filenames, cur_session_idx
    try:
        if event == mpr.Signal.Event.UPDATE:
            new_idx = session_cycling_filenames[val % len(session_cycling_filenames)]
            if new_idx != cur_session_idx:
                load_file(new_idx, True)
                cur_session_idx = new_idx
                print("Changed session to: ", new_session)
    except:
        print('exception')
        print(sig, val)

def handle_cycling_inputs():
    # TODO: get keyboard input for (h)elp, <-, ->, (e)xit
    if platform.system() == 'Windows':
        pass
    else:
        pass

def load_file(filename, should_stage=False, should_clear=True, in_bg=True):
    """loads a session file with options for staging and clearing
    
    :param filename (String): The JSON file to load
    :optional param should_stage (Boolean): Manages continuous staging and reconnecting of missing devices and signals as they appear, default false
    :optional param should_clear (Boolean): Clear all maps before loading the session, default True
    :optional param in_bg (Boolean): True if any staging should happen in a background thread, default True 
    :return (Dict): visual session information relevant to GUIs
    """

    # Parse session file
    file = open(filename)
    data = json.load(file)
    # Load session
    views = load_json(data, should_stage, should_clear, in_bg)
    return views

def load_json(session_json, should_stage=False, should_clear=True, in_bg=True):
    """loads a session JSON Dict with options for staging and clearing
    
    :param session_json (Dict): A session JSON Dict to load
    :optional param should_stage (Boolean): Manages continuous staging and reconnecting of missing devices and signals as they appear, default false
    :optional param should_clear (Boolean): Clear all maps before loading the session, default True
    :optional param in_bg (Boolean): True if any staging should happen in a background thread, default True 
    :return (Dict): visual session information relevant to GUIs
    """

    global g, staging_thread, staged_maps

    # Validate session according to schema
    schemaData = pkgutil.get_data(__name__, "mappingSessionSchema.json")
    schema = json.loads(schemaData.decode("utf-8"))
    try:
        validate(instance=session_json, schema=schema)
    except jsonschema.exceptions.ValidationError as err:
        print(err)
        return None

    # Clear current session if requested
    if should_clear:
        clear()

    if should_stage:
        staged_maps.extend(session_json["maps"])
        if staging_thread == None:
            if in_bg:
                staging_thread = threading.Thread(target = stage, daemon = True)
                staging_thread.start()
            else:
                stage()
    else:
        # Try twice to make maps (sometimes doesn't get them all on the first pass for some reason)
        g.poll(50)
        new_maps = try_make_maps(session_json["maps"])
        g.poll(50)
        session_json["maps"] = [x for x in session_json["maps"] if x not in new_maps]
        try_make_maps(session_json["maps"])

    return session_json["views"]

def clear():
    """clears all maps on the network except for connections to mappersession
    """
    global g, staged_maps, connected_maps
    staged_maps = []
    connected_maps = []
    g.poll(50)
    for map in g.maps():
        dstSigs = map.signals(mpr.Location.DESTINATION)
        # Only remove if mappersession isn't the destination
        if "mappersession" not in dstSigs[0].device()[mpr.Property.NAME]:
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