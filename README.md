# mappersession
 Session management tools in python for the libmapper signal mapping framework

## Installation

Simply run `pip install mappersession` in your python environment of choice.

## Usage

### Usage from the command-line

```
usage:
mappersession --load PATH [PATH ...] [--interactive] [--wait] [--persist] [--clear]
mappersession --unload PATH [PATH ...]
mappersession --save PATH [--description DESCRIPTION]
mappersession --print_session_tags

options:
-h, --help                  Show the help message and exit
--load PATH [PATH ...]      Mapping session JSON file(s) to load
--unload PATH [PATH ...]    Mapper session JSON file(s) to unload
--save PATH                 Save mapping session as JSON file
--interactive               Create libmapper signals for managing file
                            loading and unloading.
--wait                      Set if session should wait for missing
                            devices and signals and connected them as
                            they appear during session load
--persist                   Remain active during session load and
                            (re)create maps as they appear.
--clear                     Set if maps should be cleared after saving
                            and/or before load. Warning – this will
                            clear all maps regardless of session tag!
--print_session_tags        Print a list of active session tags
--description DESCRIPTION   Description of session, used when saving
```

Examples:

Load a session file and wait for needed signals to appear:

```
python -m mappersession --load mysession.json --wait
```

Unload a session file:

```
python -m mappersession --unload mysession.json
```

Replace a running session with another
```
python -m mappersession --unload sesh1.json --load sesh2.json
```

Start an interactive session with libmapper control signals for loading/unloading each file:

```
python -m mappersession --load session1.json session2.json --interactive
```

Save the current session and provide a description:

```
python -m mappersession --save mysession.json --description "This session does something cool"
```

### Usage as a Python module

#### Importing the module

```
import mappersession as session
```

#### Saving a mapping session file

```
session.save(filename="", description="", values=[],
             viewName="", views=[], graph=None)
```

- param `filename`: The name of the file to save
- optional param `description`: A short description of the current session
- optional param `values`: Array of {name, value} pairs for signals to set on session load
- optional param `viewName`: Name of the GUI that's adding metadata
- optional param `views`: GUI related object for recreating the session
- optional param `graph`: A previously-allocated libmapper Graph object to use. If not provided one will be allocated internally.
- return: The session JSON object

#### Loading a mapping session file

```
session.load(filename, interactive=False, wait=False, persist=False, background=False, device_map=None, graph=None)
```

Loads session files and optionally waits for signals. If the optional argument `device_map` is provided, mappersession will attempt to match the exact device and signal name, otherwise it will substitute a wildcard for the device name and map to all matching signals. In either case signals belonging to devices that have the property `hidden=True` will not be matched.

The filename will be included in the `session` property for loaded maps.

- param `filename` (String or List): The session file(s) to load
- optional param `interactive` (Boolean): Starts an interactive session for managing multiple session files. A libmapper control signal is created for corresponding to each file; setting the control signal value to a non-zero value loads the file, and setting it to zero unloads the file.
- optional param `wait` (Boolean): Wait for missing signals during session load and create maps once they appear, default `False`
- optional param `persist` (Boolean): Continue running after creating maps in session, and recreate them as matching signals (re)appear, default False
- optional param `background` (Boolean): True if waiting for signals should happen in a background thread, default False
- optional param `device_map` (Dict): A dictionary specifying correspondences between device names stored in a session file and names of devices active on the network.
- optional param `graph`: A previously-allocated libmapper Graph object to use. If not provided one will be allocated internally.
- return (Dict): visual session information relevant to GUIs

#### Unloading a mapping session file

```
session.unload(filename, graph=None)
```

Loads session files and optionally waits for signals. Maps will be tagged with the filename using a property named `session`.

- param `filename` (String or List): The session file(s) to unload
- optional param `graph`: A previously-allocated libmapper Graph object to use. If not provided one will be allocated internally.
- return (None)

#### Loading JSON-formatted session data

```
session.load_json(session_json, name=None, wait=False, persist=False, background=False, device_map=None, graph=None)
```

Loads a session JSON Dict with options for staging and clearing. If the optional argument `device_map` is provided, mappersession will attempt to match the exact device and signal name, otherwise it will substitute a wildcard for the device name and map to all matching signals. In either case signals belonging to devices that have the property `hidden=True` will not be matched.

If the optional `name` argument is provided it will be included in the  `session` property for loaded maps.

- param session_json (Dict): A session JSON Dict to load
- optional param `name` (String): A name for the session; any maps created by this session will be tagged with the name.
- optional param `wait` (Boolean): Wait for missing signals during session load and create maps once they appear, default `False`
- optional param `persist` (Boolean): Continue running after creating maps in session, and recreate them as matching signals (re)appear, default False
- optional param `background` (Boolean): True if waiting for signals should happen in a background thread, default False
- optional param `device_map` (Dict): A dictionary specifying correspondences between device names stored in a session file and names of devices active on the network.
- optional param `graph`: A previously-allocated libmapper graph object to use. If not provided one will be allocated internally.
- return (Dict): visual session information relevant to GUIs

#### Get a list of active session tags

```
session.tags(graph=None)
```

- optional param `graph`: A previously-allocated libmapper graph object to use. If not provided one will be allocated internally.
- return (List): a list of active session tags