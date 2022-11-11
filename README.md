# mappersession
 Session management tools in python for the libmapper signal mapping framework

## Installation

Simply run `pip install mappersession` in your python environment of choice.

## Usage

### From the command-line

usage: [-h] [--load PATH [PATH ...]] [--stage | --no-stage] [--clear | --no-clear]
                   [--save PATH] [--description DESCRIPTION]

optional arguments:
-h, --help : Show the help message and exit

--load PATH [PATH ...] : Session JSON file to load

--stage, --no-stage : Set if missing devices and signals should be staged and reconnected as they appear during session load, default false

--clear, --no-clear : Set if maps should be cleared during session load, default true

--save PATH : Save session as JSON file

--description DESCRIPTION : Description of session, used when saving

Examples:

Load a session, clear all maps and handle staging of missing connections:

`python -m mappersession --load mysession.json --clear --stage`

Save the current session and provide a description:

`python -m mappersession --save mysession.json --description "This session does something cool"`

### As a module

Import the module:

`import mappersession as session`

Then call save/load functions with function structures detailed below:

`session.save(filename="", description="", values=[], viewName="", views=[])`

saves the current mapping state as a JSON session file.    
- optional param filename: The JSON file to save the session into 
- optional param description: A short description of the current session
- optional param values: Array of {name, value} pairs for signals to set on session load
- optional param viewName: Name of the GUI that's adding metadata
- optional param views: GUI related object for recreating the session
- return: The session JSON object

`session.load_file(filename, should_stage=False, should_clear=True, in_bg=True)`
loads a session file with options for staging and clearing
- param filename (String): The JSON file to load
- optional param should_stage (Boolean): Manages continuous staging and reconnecting of missing devices and signals as they appear, default false
- optional param should_clear (Boolean): Clear all maps before loading the session, default True
- optional param in_bg (Boolean): True if any staging should happen in a background thread, default True 
- return (Dict): visual session information relevant to GUIs

`session.load_json(filename, should_stage=False, should_clear=True, in_bg=True)`
loads a session JSON Dict with options for staging and clearing
- param session_json (Dict): A session JSON Dict to load
- optional param should_stage (Boolean): Manages continuous staging and reconnecting of missing devices and signals as they appear, default false
- optional param should_clear (Boolean): Clear all maps before loading the session, default True
- optional param in_bg (Boolean): True if any staging should happen in a background thread, default True 
- return (Dict): visual session information relevant to GUIs