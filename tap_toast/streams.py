
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
from jsonpath_ng import parse as jparse


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
    m_schema = None
    m_metadata = None
    schema_root = '$'
    data_root = '$'
    root_key = None
    additional_keys = []
    postman_item = None

    def __init__(self, name, client=None):
        self.name = name
        self.client = client
        self.postman = Postman(name)
        self.load_masters()
        if 'root' in self.m_metadata:
            self.setRoots(self.m_schema, self.m_metadata['root'].split('.'))
        if 'root_key' in self.m_metadata:
            self.root_key = self.m_metadata['root_key']

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

    def load_masters(self):
        meta_file = get_abs_path(f'metadatas/{self.name}.json', Context.config.get('base_path'))
        if not os.path.exists(meta_file):
            raise NameError(f'Metadata file not found at {meta_file}')
        logger.info(f'Load metadata from {meta_file}')
        with open(meta_file) as f:
            self.m_metadata = json.load(f)

        schema_file = get_abs_path(f'schemas/{self.name}.json', Context.config.get('base_path'))
        if not os.path.exists(schema_file):
            raise NameError(f'Schema file not found at {schema_file}')
        logger.info(f'Load schema from {schema_file}')
        with open(schema_file) as f:
            self.m_schema = json.load(f)

    def setRoots(self, elem, roots, key_pah='$'):
        if 'type' in elem and 'array' in elem['type']:
            self.schema_root = self.schema_root + '.items'
            return self.setRoots(elem['items'], roots)

        elif 'type' in elem and 'object' in elem['type']:
            self.schema_root = self.schema_root + '.properties'
            return self.setRoots(elem['properties'], roots)

        if roots[0] not in elem:
            raise NameError(f'root path "{self.m_metadata["root"]}" not found in schema "{self.name}"')

        self.add_additional_keys(key_pah, self.schema_root)

        self.data_root = self.data_root + '.' + roots[0]
        self.schema_root = self.schema_root + '.' + roots[0]
        if len(roots) > 1:
            self.setRoots(elem[roots[0]], roots[1:], f'{key_pah}.{roots[0]}')
        else:
            if 'type' in elem[roots[0]] and 'array' in elem[roots[0]]['type']:
                self.schema_root = self.schema_root + '.items'

    def add_additional_keys(self, key_pah, schema_path):
        if 'root_keys' in self.m_metadata:
            expk = jparse(key_pah + ".key")
            keys = expk.find(self.m_metadata['root_keys'])
            for ks in keys:
                for key in ks.value:
                    exps = jparse(schema_path + f'.{key["name"]}')
                    value = exps.find(self.m_schema)[0].value
                    self.additional_keys.append({
                        "path": key_pah + f'.{key["name"]}',
                        "alias": key.get('alias', key['name']),
                        "value": value
                    })

    @property
    def schema(self):
        expr = jparse(self.schema_root)
        root = expr.find(self.m_schema)
        schema = root[0].value
        for key in self.additional_keys:
            schema['properties'].update({key['alias']: key['value']})
        return schema

    @property
    def metadata(self):
        mdata = metadata.new()
        #
        mdata = metadata.write(mdata, (), 'table-key-properties', self.m_metadata['key_properties'])
        self.postman_item = self.m_metadata['postman_item'] if 'postman_item' in self.m_metadata else self.name

        if 'replication_method' in self.m_metadata:
            mdata = metadata.write(mdata, (), 'forced-replication-method', self.m_metadata['replication_method'])

        if 'replication_key' in self.m_metadata:
            mdata = metadata.write(mdata, (), 'valid-replication-keys', [self.m_metadata['replication_key']])

        self.write_meta_recu(mdata, (), self.schema)
        return metadata.to_list(mdata)

    def write_meta_recu(self, mdata, breadcrumb, elem):
        if 'object' in elem['type'] and 'properties' in elem:
            for field_name in elem['properties'].keys():
                bread = breadcrumb + (field_name,)
                if breadcrumb == () and field_name in self.m_metadata.get('key_properties', []) or \
                        field_name == self.m_metadata.get('replication_key', ''):
                    mdata = metadata.write(mdata, bread, 'inclusion', 'automatic')
                else:
                    mdata = metadata.write(mdata, bread, 'inclusion', 'available')

                if 'array' in elem['properties'][field_name]['type']:
                    self.write_meta_recu(mdata, bread, elem['properties'][field_name]['items'])

                elif 'object' in elem['properties'][field_name]['type']:
                    s_elem = elem['properties'][field_name]
                    if 'properties' not in s_elem:
                        metadata.write(mdata, bread, 'selected', False)
                    else:
                        self.write_meta_recu(mdata, bread, s_elem)

    def is_selected(self):
        return self.stream is not None

    # The main sync function.
    def sync(self, state):
        # bookmark = self.get_bookmark(state)
        res = self.client.request(self.postman)
        logger.info(f'Sync {self.name}, res.length: {len(res)}')

        expr = jparse(self.data_root)
        for item in res:
            if self.replication_method == "INCREMENTAL":
                self.update_bookmark(state, item[self.replication_key])

            additional_keys = []
            for key in self.additional_keys:
                exp = jparse(key['path'])
                val = exp.find(item)[0].value
                additional_keys.append({key['alias']: val})

            roots = expr.find(item)
            for root in roots:

                for record in root.value:
                    for key in additional_keys:
                        record.update(key)
                    yield self.stream, record
