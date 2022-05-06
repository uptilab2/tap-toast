import os
import singer
from tap_toast.streams import Stream
import re
from tap_toast.utils import get_abs_path
from tap_toast.context import Context

logger = singer.get_logger()

def discover_streams(client):
    streams = []

    for f in os.listdir(get_abs_path(f'metadatas/', Context.config.get('base_path'))):
        m = re.match(r'([a-zA-Z_]+)\.json', f)
        if m is not None:
            s = Stream(m.group(1), client)
            schema = singer.resolve_schema_references(s.load_schema())
            metadata = s.load_metadata(schema)
            logger.info(f'Discover => stream: {s.name}, stream_alias: {s.postman_item}, tap_stream_id: {s.name}')
            streams.append({'stream': s.name, 'stream_alias': s.postman_item, 'tap_stream_id': s.name, 'schema': schema,
                            'metadata': metadata})
    return streams

