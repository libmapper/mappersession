# mappersession
 Session management tools in python for the libmapper signal mapping framework

## Installation

Simply run `pip install mappersession` in your python environment of choice.

## Usage

### Usage from the command-line

usage: [-h] [--load PATH [PATH ...]] [--wait | --no-wait] [--clear | --no-clear]
                   [--save PATH] [--description DESCRIPTION]

optional arguments:
-h, --help : Show the help message and exit

--load PATH [PATH ...] : Session JSON file(s) to load

--unload PATH [PATH ...] : Session JSON file(s) to unload

--wait, --no-wait : Set if session should wait for missing devices and signals and connected them as they appear during session load, default False

--clear, --no-clear : Set if maps should be cleared after saving and/or before load, default false

--save PATH : Save session as JSON file

--description DESCRIPTION : Description of session, used when saving

Examples:

Clear all active maps, load a session file and wait for needed signals to appear:

```
python -m mappersession --load mysession.json --clear --wait
```

Unload a session file:

```
python -m mappersession --unload mysession.json
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

loads session files and optionally waits for signals. Maps will be tagged with the filename using a property named `session`.

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

loads session files and optionally waits for signals. Maps will be tagged with the filename using a property named `session`.

- param `filename` (String or List): The session file(s) to unload
- optional param `graph`: A previously-allocated libmapper Graph object to use. If not provided one will be allocated internally.
- return (None)

#### Loading JSON-formatted session data

```
session.load_json(session_json, name=None, wait=False, persist=False, background=False, device_map=None, graph=None)
```

loads a session JSON Dict with options for staging and clearing

- param session_json (Dict): A session JSON Dict to load
- optional param `name` (String): A name for the session; any maps created by this session will be tagged with the name.
- optional param `wait` (Boolean): Wait for missing signals during session load and create maps once they appear, default `False`
- optional param `persist` (Boolean): Continue running after creating maps in session, and recreate them as matching signals (re)appear, default False
- optional param `background` (Boolean): True if waiting for signals should happen in a background thread, default False
- optional param `device_map` (Dict): A dictionary specifying correspondences between device names stored in a session file and names of devices active on the network.
- optional param `graph`: A previously-allocated libmapper graph object to use. If not provided one will be allocated internally.
- return (Dict): visual session information relevant to GUIs
