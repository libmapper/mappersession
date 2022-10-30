import sys
import argparse

def createParser():
    parser = argparse.ArgumentParser(description="Save or load a mapping session")
    parser.add_argument(
        '--load', type=argparse.FileType('r'),
        metavar='PATH',
        help="Session JSON file to load")
    parser.add_argument(
        '--stage', action=argparse.BooleanOptionalAction,
        help="Set if missing devices and signals should be staged and reconnected as they appear during session load")
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

if __name__ == '__main__':
    import mappersession as session
    # Parse arguments
    parser = createParser()
    args = parser.parse_args()
    if (args.save is not None):
        session.save(args.save, args.description if args.description != None else "")
    elif (args.load is not None):
        should_stage = args.stage if args.stage != None else False
        should_clear = args.clear if args.clear != None else True
        session.load_file(args.load.name, should_stage, should_clear)
    elif (args.clear is not None):
        session.clear()
    else:
        print("Not enough arguments provided, please use --save or --load with JSON file path(s)")