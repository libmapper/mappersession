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
import itertools, signal

current_fileversion = "2.4"
g = None
staging_thread = None
stop_session = False

# Bookkeeping for maps
staged_maps = []
# Session files
session_filenames = []

def handler_stop_session(signum, frame):
    global stop_session
    stop_session = True
    if staging_thread != None:
        staging_thread.stop()

signal.signal(signal.SIGINT, handler_stop_session)
signal.signal(signal.SIGTERM, handler_stop_session)

def check_graph(graph, sync=True):
    global g
    if not graph:
        g = mpr.Graph()
        if sync:
            print('syncing graph...')
            g.poll(2000)
    else:
        g = graph
    return g

def save(filename="", description="", values=[], view_name="", views=[], graph=None):
    """saves the current mapping state as a JSON session file.

    :optional param filename (String): The JSON file to save the session into
    :optional param description (String): A short description of the current session
    :optional param values (List): Array of signal {name, value} pairs to set on session load
    :optional param view_name (String): Name of the GUI that's adding metadata
    :optional param views (List): GUI related object for recreating the session
    :optional param graph (libmapper Graph object): A previously-allocated libmapper graph object to use. If not provided one will be allocated internally.
    :return (Dict): The session JSON object
    """

    # Create JSON from network state following the schema
    session = {}
    session["fileversion"] = current_fileversion
    session["description"] = description.strip("'")
    session["values"] = values
    session["views"] = views

    graph = check_graph(graph)

    # Populate maps
    print("Collecting maps from network...")
    session["maps"] = []
    for map in graph.maps():

        # omit 'hidden' devices
        if any([sig.device()["hidden"] for sig in map.signals()]):
            print("Skipping hidden device")
            continue

        newMap = {}
        # Source signals
        newMap["sources"] = [(sig.device()[mpr.Property.NAME] + "/" + sig[mpr.Property.NAME])
                             for sig in map.signals(mpr.Location.SOURCE)]

        # Destination signals
        newMap["destinations"] = [(sig.device()[mpr.Property.NAME] + "/" + sig[mpr.Property.NAME])
                                  for sig in map.signals(mpr.Location.DESTINATION)]

        # Other properties
        # TODO: need to save ALL map properties!
        newMap["expression"] = map[mpr.Property.EXPRESSION]
        newMap["muted"] = map[mpr.Property.MUTED]
        newMap["process_loc"] = map[mpr.Property.PROCESS_LOCATION].name
        newMap["protocol"] = map[mpr.Property.PROTOCOL].name
        newMap["scope"] = [dev[mpr.Property.NAME] for dev in map[mpr.Property.SCOPE]]
        newMap["use_inst"] = map[mpr.Property.USE_INSTANCES]
        newMap["version"] = map[mpr.Property.VERSION]

        # Add to maps
        session["maps"].append(newMap)

    # Save into the file
    if filename != "":
        with open(filename.strip("'"), 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=4)
            print("Saved session as: " + filename)
    return session

# Internal staging method to be used in a thread
# maps that should be staged should be added to the global 'staged_maps'
def wait_for_sigs(persist=False):
    global g, staged_maps

    while not stop_session and (len(staged_maps) or persist):
        # Try to create any staged maps that we can
        try:
            # TODO: don't bother running this unless new devices have appeared
            g.poll(1000)
            new_maps = try_make_maps(g, staged_maps, None)
            if not persist:
                for new_map in new_maps:
                    staged_maps.remove(new_map)
        except:
            pass

# Attempts to create any eligible maps that have all sources and destination present 
def try_make_maps(graph, maps, device_map=None):

    new_maps = []
    for map in maps:
        # Check if the map's signals are available
        # Match signals with different device names for mapping transportability
        
        srcs = [find_sigs(graph, s, device_map) for s in map["sources"]]
        dsts = find_sigs(graph, map["destinations"][0], device_map)

        for d in dsts:
            for s in list(itertools.product(*srcs)):
                # Create map and remove from staged list
                new_map = mpr.Map(list(s), d)
                if not new_map:
                    print('error: failed to create map', map["sources"], "->", map["destinations"])
                    continue
                print('created map: ', map["sources"], "->", map["destinations"])

                # Set map properties
                # TODO: need to iterate through ALL properties!

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
                # TODO: map scope property may need to be translated
                # new_map[mpr.Property.SCOPE] = map["scope"]
                new_map[mpr.Property.USE_INSTANCES] = map["use_inst"]
                new_map[mpr.Property.VERSION] = map["version"]

                # TODO: session property should be an array
                if 'session' in map:
                    new_map['session'] = map['session']

                # Push to network
                new_map.push()
                new_maps.append(map.copy())
    graph.poll()
    return new_maps

def start_session(graph, filenames):
    """start an interactive session. A libmapper signal is created for loading/unloading each file.
    
    :param filenames (String or List): The JSON files to load
    :return (None): Blocks while executing, should CTL+C or hit 'e' to exit
    """

    graph = check_graph(graph, sync=False)

    global session_filenames, stop_session
    session_filenames = filenames

    # Set up libmapper signal that controls the current session index
    dev = mpr.Device("mappersession", graph)
    for filename in session_filenames:
        signame = filename.removesuffix(".json").split('/')[-1]
        # TODO: need to handle duplicate filenames?
        sig = dev.add_signal(mpr.Direction.INCOMING, signame, 1, mpr.Type.INT32,
                             None, 0, 1, None, cur_session_handler)
        sig.set_property("filename", filename, publish=False)

    while (not stop_session):
        dev.poll(50)

    dev.free()
    if graph is not None:
        graph.free()

def cur_session_handler(sig, event, id, val, timetag):
    global session_filenames
    try:
        if event == mpr.Signal.Event.UPDATE:
            filename = sig['filename']
            if val == 0:
                print('unloading', filename)
                unload(filename, graph = sig.graph())
            else:
                print('loading', filename)
                load(filename, graph = sig.graph())
    except:
        print('exception')
        print(sig, val)

def load(filename, interactive=False, wait=False, persist=False, background=False, device_map=None, graph=None):
    """loads a session file with options for staging

    :param filenames (String or List): The JSON file(s) to load
    :optional param interactive (Boolean): Create libmapper signals for controlling session loading/unloading, default False
    :optional param wait (Boolean): Wait for missing signals and create maps when they appear, default False
    :optional param persist (Boolean): Continue running after creating maps in session, and recreate them as matching signals (re)appear, default False
    :optional param background (Boolean): Wait for missing signals in a background thread, default True
    :optional param graph (libmapper Graph object): A previously-allocated libmapper graph object to use. If not provided one will be allocated internally.
    :return (Dict): visual session information relevant to GUIs
    """

    if interactive:
        return start_session(graph, filename)

    if not isinstance(filename, list):
        filename = [filename]
    views = []

    for name in filename:
        # Parse session file
        file = open(name)
        data = json.load(file)
        # Load session
        views.extend(load_json(data, name, wait, persist, background, device_map, graph))
    return views

def load_json(session_json, name=None, wait=False, persist=False, background=False, device_map=None, graph=None):
    """loads a session JSON Dict with options for staging

    :param session_json (Dict): A session JSON Dict to load
    :optional param name (String): Tag for maps created for this session
    :optional param wait (Boolean): Manages continuous staging and reconnecting of missing devices and signals as they appear, default False
    :optional param persist (Boolean): Continue running after creating maps in session, and recreate them as matching signals (re)appear, default False
    :optional param background (Boolean): True if any staging should happen in a background thread, default True
    :optional param graph (libmapper Graph object): A previously-allocated libmapper graph object to use. If not provided one will be allocated internally.
    :return (Dict): visual session information relevant to GUIs
    """

    global staging_thread, staged_maps, current_fileversion

    graph = check_graph(graph)

    # Update json if fileversion doesn't match current schema
    session_json = upgrade_json(session_json)

    if 'maps' in session_json and name is not None:
        name = name.removesuffix(".json").split('/')[-1]
        for map in session_json['maps']:
            map['session'] = name

    # Validate session according to schema
    schemaData = pkgutil.get_data(__name__, "mappingSessionSchema.json")
    schema = json.loads(schemaData.decode("utf-8"))
    try:
        validate(instance=session_json, schema=schema)
    except jsonschema.exceptions.ValidationError as err:
        print(err)
        return None

    if wait or persist:
        staged_maps.extend(session_json["maps"])
        if staging_thread == None:
            if background:
                staging_thread = threading.Thread(target = wait_for_sigs, daemon = True)
                staging_thread.start()
            else:
                wait_for_sigs(persist)
    else:
        new_maps = try_make_maps(graph, session_json["maps"], device_map)

    return session_json["views"]

def unload(filename, graph=None):
    """unloads session files

    :param filename (String or List): The JSON file(s) to unload
    :optional param graph (libmapper Graph object)
    """

    # for now we will just clear maps with matching session tags
    # TODO: restore maps that belong to other loaded sessions

    graph = check_graph(graph)

    if not isinstance(filename, list):
        filename = [filename]

    for name in filename:
        name = name.removesuffix(".json").split('/')[-1]
        print("unloading session tag", name)
        clear(name, graph)

def clear(tag=None, graph=None):
    """clears maps on the network except for those connected to mappersession
    """

    graph = check_graph(graph)

    maps = graph.maps()
    if tag:
        maps = maps.filter('session', tag)
    for map in maps:
        dstSigs = map.signals(mpr.Location.DESTINATION)
        # Only remove if mappersession isn't the destination
        if "mappersession" in dstSigs[0].device()[mpr.Property.NAME]:
            continue
        print("  unloading map:", [s for s in map.signals(mpr.Location.SOURCE)],
              "->", [s for s in map.signals(mpr.Location.DESTINATION)])
        map.release()
    graph.poll()

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

def upgrade_json(session_json):
    global current_fileversion
    if session_json["fileversion"] == current_fileversion:
        return session_json
    version = float(session_json["fileversion"])
    if version < 2.0 or version > float(current_fileversion):
        print("Failed to load session with unsupported version: ", version)
        return
    print("Loading legacy file with version: ", version)
    print("Consider re-saving the session to update to the most recent version.")
    session_json["maps"] = []
    session_json["description"] = ""
    session_json["views"] = [] # Unable to use legacy views, some fields are not present
    session_json["values"] = []
    maps = session_json["mapping"]["connections"] if version <= 2.1 else session_json["mapping"]["maps"] if version <= 2.3 else session_json["maps"]

    for map in maps:
        newMap = {"sources": [], "destinations": []}
        # Add sources and destinations
        if version == 2.0:
            srcKey = "source"
            dstKey = "destination"
        elif version == 2.1:
            srcKey = "src"
            dstKey = "dest"
        else: # 2.2 and 2.3
            srcKey = "sources"
            dstKey = "destinations"
        for src in map[srcKey]:
            srcName = src[1:] if version <= 2.2 else src["name"]
            newMap["sources"].append(srcName)
        for dst in map[dstKey]:
            dstName = dst[1:] if version <= 2.2 else dst["name"]
            newMap["destinations"].append(dstName)
        # Add other fields
        # TODO: need to iterate through ALL properties!
        # Fix expressions that use legacy signal identifiers
        newExp = map["expression"].replace("src[0]", "x").replace("src", "x")\
                                  .replace("dest[0]", "y").replace("dest", "y")\
                                  .replace("dst[0]", "y").replace("dst", "y")\
                                  .replace("s[0]", "x").replace("d[0]", "y")
        newMap["expression"] = newExp
        if "mute" in map: # <= 2.2
            newMap["muted"] = map["mute"] == 1
        elif "muted" in map: # 2.3
            newMap["muted"] = map["muted"]
        else: # Unmute by default
            newMap["muted"] = False
        if "mode" in map:
            if map["mode"] == "reverse": # <= 2.1
                newMap["expression"] = "y=x"
                tmpSrcs = newMap["sources"].copy()
                newMap["sources"] = newMap["destinations"]
                newMap["destinations"] = tmpSrcs
            if map["mode"] == "linear": # 2.2
                newMap["expression"] = "y=linear(x,-,-,-,-)"
        if "calibrating" in map[dstKey][0]: # 2.2
            if map[dstKey][0]["calibrating"] == True:
                newMap["expression"] = "y=linear(x,?,?,-,-)"
        if version <= 2.2:
            newMap["process_loc"] = "SOURCE"
            newMap["protocol"] = "UDP"
            newMap["use_inst"] = False
            newMap["version"] = 0
        else: # 2.3
            newMap["process_loc"] = map["process_loc"]
            newMap["protocol"] = map["protocol"]
            newMap["scope"] = map["scope"]
            newMap["use_inst"] = map["use_inst"]
            newMap["version"] = map["version"]
        session_json["maps"].append(newMap)

    if "mapping" in session_json:
        del session_json["mapping"]
    session_json["fileversion"] = current_fileversion # Not really necessary I suppose
    return session_json

def find_sigs(graph, fullname, device_map=None):
    names = fullname.split('/', 1)

    '''
    If device_map dictionary is provided we will attempt to match the exact device name,
    otherwise we substitute a wildcard for the ordinal and return an array of all matching signals
    '''

    ret = []

    if device_map and names[0] in device_map:
        names[0] = device_map[names[0]]
        print("searching for exact match with device:signal name '{0}:{1}'".format(names[0], names[1]))
        dev = graph.devices().filter(mpr.Property.NAME, names[0])
        if dev:
            sig = dev.next().signals().filter(mpr.Property.NAME, names[1])
            if sig:
                ret = [sig.next()]
    else:
        print("searching for wildcard match with device:signal name '*:{0}'".format(names[1]))
        sigs = graph.signals().filter(mpr.Property.NAME, names[1])
        for sig in sigs:
            ret.append(sig)
    return ret
