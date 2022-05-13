
#
# Module dependencies.
#
import re
import os
import sys
import logging
from tap_toast.context import Context
from tap_toast.postman import Postman
from tap_toast.utils import get_abs_path
from tap_toast.streams import Stream
import singer
import singer.metrics as metrics
from singer import metadata
from singer import Transformer

logger = logging.getLogger()


class Client(object):
    authentication = None
    post_process = None

    def __init__(self):
        if 'authentication_postman' in Context.config:
            name = {
                "filename": Context.config['authentication_postman'],
                "item": Context.config['authentication_postman']
            }
            self.authentication = Postman(name)

    @staticmethod
    def do_discover():
        streams = []

        for f in os.listdir(get_abs_path(f'metadatas/', Context.config.get('base_path'))):
            m = re.match(r'([a-zA-Z_]+)\.json', f)
            if m is not None:
                s = Stream(m.group(1))
                if s.isValid:
                    schema = singer.resolve_schema_references(s.schema)
                    metadata = s.metadata
                    logger.info(
                        f'Discover => stream: {s.name}, stream_alias: {s.postman_item}, tap_stream_id: {s.name}')
                    streams.append({'stream': s.name, 'stream_alias': s.postman_item, 'tap_stream_id': s.name,
                                    'schema': schema, 'metadata': metadata})
        return {"streams": streams}

    @staticmethod
    def get_selected_streams(catalog):
        selected_stream_names = []
        for stream in catalog.streams:
            if stream.schema.selected:
                selected_stream_names.append(stream.tap_stream_id)
        return selected_stream_names

    @staticmethod
    def sync_stream(state, instance):
        stream = instance.stream

        with metrics.record_counter(stream.tap_stream_id) as counter:
            for (stream, record) in instance.sync(state):
                counter.increment()

                with Transformer() as transformer:
                    record = transformer.transform(record, stream.schema.to_dict(), metadata.to_map(stream.metadata))

                singer.write_record(stream.tap_stream_id, record)
                # NB: We will only write state at the end of a stream's sync:
                #  We may find out that there exists a sync that takes too long and can never emit a bookmark
                #  but we don't know if we can guarentee the order of emitted records.

            if instance.replication_method == "INCREMENTAL":
                singer.write_state(state)

            return counter.value

    def do_sync(self, catalog, state):
        selected_stream_names = Client.get_selected_streams(catalog)

        for stream in catalog.streams:
            stream_name = stream.tap_stream_id

            mdata = singer.metadata.to_map(stream.metadata)

            if stream_name not in selected_stream_names:
                continue

            key_properties = singer.metadata.get(mdata, (), 'table-key-properties')
            singer.write_schema(stream_name, stream.schema.to_dict(), key_properties)

            logger.info("%s: Starting sync", stream_name)
            instance = Stream(stream_name, self.authentication, self.post_process)
            if not instance.isValid:
                raise NameError(f'Stream {stream_name} missing postman file')
            instance.stream = stream
            counter_value = Client.sync_stream(state, instance)
            logger.info("%s: Completed sync (%s rows)", stream_name, counter_value)



