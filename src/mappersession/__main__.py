import sys
import argparse

def createParser():
    parser = argparse.ArgumentParser(description="Save or load a mapping session")
    parser.add_argument(
        '--load', type=argparse.FileType('r'),
        nargs='+',
        metavar='PATH',
        help="Mapping session file(s) to load")
    parser.add_argument(
        '--unload', type=argparse.FileType('r'),
        nargs='+',
        metavar='PATH',
        help="Mapping session file(s) to unload")
    parser.add_argument(
        '--save', type=ascii,
        metavar='PATH',
        help="Save mapping session as JSON file")
    parser.add_argument(
        '--clear', action=argparse.BooleanOptionalAction,
        help="Clear currently active maps")
    parser.add_argument(
        '--print_session_tags', action=argparse.BooleanOptionalAction,
        help="Print a list of active session tags")
    parser.add_argument(
        '--wait', action=argparse.BooleanOptionalAction,
        help="Wait for missing signals during session load and create maps once they appear.")
    parser.add_argument(
        '--persist', action=argparse.BooleanOptionalAction,
        help="Remain active during session load and (re)create maps as they appear.")
    parser.add_argument(
        '--interactive', action=argparse.BooleanOptionalAction,
        help="Create libmapper signals for managing file loading and unloading.")
    parser.add_argument(
        '--description', type=ascii,
        help="Description of session, used when saving")
    # TODO:
    # Overwrite save file
    #
    return parser

if __name__ == '__main__':
    try:
        import mappersession as session
    except:
        try:
            sys.path.append(
                            os.path.join(os.path.join(os.getcwd(),
                                                      os.path.dirname(sys.argv[0])),
                                         './mappersession'))
            import mappersession as session
        except:
            print('Error importing mappersession module.')
            sys.exit(1)

    # Parse arguments
    parser = createParser()
    args = parser.parse_args()
    should_clear = args.clear if args.clear != None else False

    if (args.save is not None):
        session.save(args.save, args.description if args.description != None else "")
    if should_clear:
        # clear after save and before load
        session.clear()
    elif (args.unload is not None):
        filenames = [path.name for path in args.unload]
        session.unload(filenames)
    if (args.load is not None):
        interactive = args.interactive if args.interactive != None else False
        wait = args.wait if args.wait != None else False
        persist = args.persist if args.persist != None else False
        filenames = [path.name for path in args.load]
        session.load(filenames, interactive=interactive, wait=wait, persist=persist)
    if (args.print_session_tags is not None):
        print('active session tags:', session.tags())
