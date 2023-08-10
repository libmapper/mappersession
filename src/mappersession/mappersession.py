import sys
import platform
import json
import jsonschema
import libmapper as mpr
from jsonschema import validate
import pkgutil
import threading
import re
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
        props = map.properties.copy()
        for key in props:
            val = props[key]
            if key == "expr":
                newMap["expression"] = val
            if key == "process_loc":
                newMap[key] = val.name
            elif key == "protocol":
                newMap[key] = val.name
            elif key == "scope":
                if val is not None:
                    newMap[key] = [dev[mpr.Property.NAME] for dev in val]
            elif key == "status":
                newMap[key] = val.name
            elif key == "is_local" or key == "num_sigs_in":
                pass
            else:
                newMap[key] = val

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
        src_list_list = list(itertools.product(*srcs))
        dsts = find_sigs(graph, map["destinations"][0], device_map)

        for dst in dsts:
            for src_list in src_list_list:
                # Check if map already exists
#                pre = graph.maps().filter(mpr.Property.DESTINATION, dst)
#                if pre:
#                    print('found existing maps with matching dest, should we check them?')

                # Create map
                new_map = mpr.Map(list(src_list), dst)
                if not new_map:
                    print("error: failed to create map", map["sources"], "->", map["destinations"])
                    continue
                print("created map:", [s for s in new_map.signals(mpr.Location.SOURCE)],
                      "->", [s for s in new_map.signals(mpr.Location.DESTINATION)])

                # when maps are created the source signals are alphabetised to create a standard representation
                # if our source signals have swapped position we need to edit the expression
                old_idx = 0
                newExp = map["expression"]
                if len(src_list) > 1:
                    for i in list(src_list):
                        new_idx = new_map.index(i)
                        if new_idx != old_idx:
                            print('need to remap expression sources:', old_idx, '->', new_idx)
                            newExp = re.sub(r'x\$({0})'.format(old_idx), r'x${0}'.format(new_idx), newExp)
                        old_idx = old_idx + 1
                print('setting expression to', newExp)
                new_map[mpr.Property.EXPRESSION] = newExp

                # Set map properties
                for key in map:
                    val = map[key]
                    if key == "sources" or key == "destinations" or key == "expression":
                        pass # already handled
                    elif key == "muted":
                        new_map[mpr.Property.MUTED] = val
                    elif key == "process_loc":
                        if val == 'SOURCE' or val == 'src':
                            new_map[mpr.Property.PROCESS_LOCATION] = mpr.Location.SOURCE
                        elif val == 'DESTINATION' or val == 'dst':
                            new_map[mpr.Property.PROCESS_LOCATION] = mpr.Location.DESTINATION
                    elif key == "protocol":
                        if val == 'udp' or val == 'UDP':
                            new_map[mpr.Property.PROTOCOL] = mpr.Protocol.UDP
                        elif val == 'tcp' or val == 'TCP':
                            new_map[mpr.Property.PROTOCOL] = mpr.Protocol.TCP
                    elif key == "scope":
                        # TODO: Remove existing scopes?

                        # Map scope property may need to be translated!
                        for scope in map["scope"]:
                            src_dev_names = [sig_name.split('/', 1)[0] for sig_name in map["sources"]]
                            if scope in src_dev_names:
                                idx = [sig_name.split('/', 1)[0] for sig_name in map["sources"]].index(scope)
                                # Look up corresponding device in actual map.
                                # Use src_list here since order may be different in new_map.signals()
                                new_map.add_scope(src_list[idx].device())
                            elif scope == map["destinations"][0].split('/', 1)[0]:
                                new_map.add_scope(dst.device())
                            else:
                                dev = graph.devices().filter(mpr.Property.NAME, scope)
                                if dev:
                                    new_map.add_scope(dev.next())
                                else:
                                    print('failed to find scope device named', scope)
                    elif key == "session":
                        # TODO: session property should be an array
                        new_map[key] = val
                    else:
                        new_map[key] = val

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

        for key in map:
            val = map[key]
            if key == srcKey or key == dstKey:
                pass
            elif key == "expression" or key == "expr":
                # Fix expressions that use legacy signal identifiers
                print('upgrading expression...')
                print('  ', val)
                newExp = re.sub(r'(dest|dst)\[([\d+])\]', r'y$\2', val)\
                           .replace('dest', 'y')\
                           .replace('dst', 'y')
                print('  ', newExp)
                newExp = re.sub(r'src\[([\d+])\]', r'x$\1', newExp)\
                           .replace('src', 'x')
                print('  ', newExp)
                if version <= 2.0:
                    # TODO: make sure we are not garbling functions!
                    # ok if string as nothing before/after except operator or bracket
                    newExp = re.sub(r'd\[([\d+])\]', r'y$\1', newExp)
                    newExp = re.sub(r's\[([\d+])\]', r'x$\1', newExp)
                print('  ', newExp)
                newMap["expression"] = newExp
            elif key == "mute": # <= 2.2
                newMap["muted"] = (val == 1)
            elif key == "mode":
                if val == "reverse": # <= 2.1
                    newMap["expression"] = "dst[0]=src[0]"
                    tmpSrcs = newMap["sources"].copy()
                    newMap["sources"] = newMap["destinations"]
                    newMap["destinations"] = tmpSrcs
                if val == "linear": # 2.2
                    newMap["expression"] = "y=linear(x,-,-,-,-)"
            else:
                newMap[key] = val
        if version <= 2.2:
            # add some missing metadata - not actually necessary since these are the defaults
            newMap["process_loc"] = "SOURCE"
            newMap["protocol"] = "UDP"
            newMap["use_inst"] = False
            newMap["version"] = 0
        if "calibrating" in map[dstKey][0]: # 2.2
            if map[dstKey][0]["calibrating"] == True:
                newMap["expression"] = "y=linear(x,?,?,-,-)"
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
        if dev and not dev['hidden']:
            sig = dev.next().signals().filter(mpr.Property.NAME, names[1])
            if sig:
                ret = [sig.next()]
    else:
        print("searching for wildcard match with device:signal name '*:{0}'".format(names[1]))
        sigs = graph.signals().filter(mpr.Property.NAME, names[1])
        for sig in sigs:
            if not sig.device()['hidden']:
                ret.append(sig)

    return ret
