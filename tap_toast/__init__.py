import json
import sys
import singer
from singer import metadata
from tap_toast.client import Client
from tap_toast.discover import discover_streams
from tap_toast.sync import sync_stream
from tap_toast.streams import Stream
from tap_toast.context import Context


LOGGER = singer.get_logger()


def do_discover(cli):
    LOGGER.info("Starting discover")
    catalog = {"streams": discover_streams(cli)}
    json.dump(catalog, sys.stdout, indent=2)
    LOGGER.info("Finished discover")


def stream_is_selected(mdata):
    return mdata.get((), {}).get('selected', False)


def get_selected_streams(catalog):
    selected_stream_names = []
    for stream in catalog.streams:
        # mdata = metadata.to_map(stream.metadata)
        if stream.schema.selected:
            selected_stream_names.append(stream.tap_stream_id)
    return selected_stream_names


def do_sync(cli, catalog, state):
    selected_stream_names = get_selected_streams(catalog)

    for stream in catalog.streams:
        stream_name = stream.tap_stream_id

        mdata = metadata.to_map(stream.metadata)

        if stream_name not in selected_stream_names:
            continue

        key_properties = metadata.get(mdata, (), 'table-key-properties')
        singer.write_schema(stream_name, stream.schema.to_dict(), key_properties)

        LOGGER.info("%s: Starting sync", stream_name)
        instance = Stream(stream_name, cli)
        if not instance.isValid:
            raise NameError(f'Stream {stream_name} missing postman file')
        instance.stream = stream
        counter_value = sync_stream(state, instance)
        LOGGER.info("%s: Completed sync (%s rows)", stream_name, counter_value)

    LOGGER.info("Finished sync")


# @singer.utils.handle_top_exception(LOGGER)
def main():
    parsed_args = singer.utils.parse_args([])

    Context.config = parsed_args.config
    cli = Client()

    if parsed_args.discover:
        do_discover(cli)
    elif parsed_args.catalog:
        state = parsed_args.state or {}
        do_sync(cli, parsed_args.catalog, state)
    LOGGER.info("Finished tap")


if __name__ == "__main__":
    main()
