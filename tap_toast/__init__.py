import json
import sys
import singer
from tap_toast.client import Client
from tap_toast.context import Context
from tap_toast.utils import readNextPage

LOGGER = singer.get_logger()


# @singer.utils.handle_top_exception(LOGGER)
def main():
    parsed_args = singer.utils.parse_args([])

    Context.config = parsed_args.config
    cli = Client()
    cli.post_process = readNextPage

    if parsed_args.discover:
        catalog = cli.do_discover()
        json.dump(catalog, sys.stdout, indent=2)
    elif parsed_args.catalog:
        state = parsed_args.state or {}
        cli.do_sync(parsed_args.catalog, state)
    LOGGER.info("Finished tap")


if __name__ == "__main__":
    main()
