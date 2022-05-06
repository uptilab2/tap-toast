
#
# Module dependencies.
#

import json
import os.path

import singer
from singer import metadata
from singer import utils
from dateutil.parser import parse
from tap_toast.context import Context
from tap_toast.postman import Postman
from tap_toast.utils import get_abs_path


logger = singer.get_logger()


def needs_parse_to_date(string):
    if isinstance(string, str):
        try:
            parse(string)
            return True
        except ValueError:
            return False
    return False


class Stream:
    name = None
    replication_method = None
    replication_key = None
    stream = None
    session_bookmark = None
    postman = None

    def __init__(self, name, client=None):
        self.name = name
        self.client = client
        self.postman = Postman(name)

    @property
    def isValid(self):
        return self.postman.isValid

    def get_bookmark(self, state):
        bookmark = singer.get_bookmark(state, self.name, self.replication_key)
        if bookmark is None:
            singer.write_bookmark(state, self.name, self.replication_key, None)
            bookmark = singer.get_bookmark(state, self.name, self.replication_key)
        return bookmark

    def update_bookmark(self, state, value):
        # if self.is_bookmark_old(state, value):
        singer.write_bookmark(state, self.name, self.replication_key, value)

    def is_bookmark_old(self, state, value):
        current_bookmark = self.get_bookmark(state)
        return utils.strptime_with_tz(value) > utils.strptime_with_tz(current_bookmark)

    def load_schema(self):
        schema_file = get_abs_path(f'schemas/{self.name}.json', Context.config.get('base_path'))
        if not os.path.exists(schema_file):
            raise NameError(f'Schema file not found at {schema_file}')
        logger.info(f'Load schema from {schema_file}')
        with open(schema_file) as f:
            schema = json.load(f)
        return schema

    def load_metadata(self, schema):
        meta_file = get_abs_path(f'metadatas/{self.name}.json', Context.config.get('base_path'))
        if not os.path.exists(meta_file):
            raise NameError(f'Metadata file not found at {meta_file}')
        logger.info(f'Load metadata from {meta_file}')
        with open(meta_file) as f:
            meta = json.load(f)

        mdata = metadata.new()
        #
        mdata = metadata.write(mdata, (), 'table-key-properties', meta['key_properties'])
        self.postman_item = meta['postman_item'] if 'postman_item' in meta else self.name

        if 'replication_method' in meta:
            mdata = metadata.write(mdata, (), 'forced-replication-method', meta['replication_method'])

        if 'replication_key' in meta:
            mdata = metadata.write(mdata, (), 'valid-replication-keys', [meta['replication_key']])

        for field_name in schema['properties'].keys():
            if field_name in meta.get('key_properties', []) or field_name == meta.get('replication_key', ''):
                mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'automatic')
            else:
                mdata = metadata.write(mdata, ('properties', field_name), 'inclusion', 'available')

        return metadata.to_list(mdata)

    def is_selected(self):
        return self.stream is not None

    # The main sync function.
    def sync(self, state):
        bookmark = self.get_bookmark(state)
        res = self.client.request(self.postman)

        logger.info(f'Sync {self.name}, res.length: {len(res)}')

        for item in res:
            if self.replication_method == "INCREMENTAL":
                self.update_bookmark(state, item[self.replication_key])
            if self.name in item:
                for v in item[self.name]:
                    yield self.stream, v
            else:
                yield self.stream, item

