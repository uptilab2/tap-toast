import json
import sys
import singer
from singer import metadata
from tap_toast.toast import Toast
from tap_toast.discover import discover_streams
from tap_toast.sync import sync_stream
from tap_toast.streams import Stream
from tap_toast.context import Context


LOGGER = singer.get_logger()

REQUIRED_CONFIG_KEYS = [
    "client_id",
    "client_secret",
    "location_guid",
    "start_date",
    "hostname",
    "postman"
]


def do_discover(client):
    LOGGER.info("Starting discover")
    catalog = {"streams": discover_streams(client)}
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


class DependencyException(Exception):
    pass


# def populate_class_schemas(catalog, selected_stream_names):
#     for stream in catalog.streams:
#         if stream.tap_stream_id in selected_stream_names:
#             STREAMS[stream.tap_stream_id].stream = stream
#



def do_sync(client, catalog, state):
    selected_stream_names = get_selected_streams(catalog)

    for stream in catalog.streams:
        stream_name = stream.tap_stream_id

        mdata = metadata.to_map(stream.metadata)

        if stream_name not in selected_stream_names:
            continue

        key_properties = metadata.get(mdata, (), 'table-key-properties')
        singer.write_schema(stream_name, stream.schema.to_dict(), key_properties)

        LOGGER.info("%s: Starting sync", stream_name)
        instance = Stream(stream_name, client)
        if not instance.isValid:
            raise NameError(f'Stream {stream_name} missing postman file')
        instance.stream = stream
        counter_value = sync_stream(state, instance)
        LOGGER.info("%s: Completed sync (%s rows)", stream_name, counter_value)
        singer.write_state(state)

    LOGGER.info("Finished sync")
    singer.write_state(state)


# @singer.utils.handle_top_exception(LOGGER)
def main():
    parsed_args = singer.utils.parse_args([])

    Context.config = parsed_args.config
    client = Toast()

    if parsed_args.discover:
        do_discover(client)
    elif parsed_args.catalog:
        state = parsed_args.state or {}
        do_sync(client, parsed_args.catalog, state)
    LOGGER.info("Finished tap")


if __name__ == "__main__":
    main()
