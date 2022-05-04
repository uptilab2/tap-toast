import json
import re
from tap_toast.context import Context
from jsonpath_ng import parse
from tap_toast.utils import get_abs_path


def setVars(string):
    for group in re.findall(r'{{([a-zA-Z_-]*)}}', string):
        string = string.replace(f'{{{{{group}}}}}', Context.config[group])
    return string


def getHeaderFromBody (body):
    if body['mode'] == 'raw':
        if 'options' in body:
            if body['options']['raw']['language'] == 'json':
                return {'Content-Type': 'application/json'}


class Postman:
    events = []
    request = None

    def __init__(self, name, key):
        file = json.load(open(get_abs_path(f'postman/{name}.json')))
        self.readItemConfig(file, key)
        self.isAnonymous = 'auth' not in file

    def readItemConfig(self, file, name):
        for item in file['item']:
            if item['name'] == name:
                self.request = item['request']
                if 'event' in item:
                    for event in item['event']:
                        if 'variable' in event:
                            self.events.append(event)

    @property
    def url(self):
        _url = self.request['url']
        res = _url['host'][0]
        if 'path' in _url:
            for p in _url['path']:
                res = res + f'/{p}'
        if 'query' in _url:
            qs = ''
            for q in _url['query']:
                qs = qs + f'&{q["key"]}={q["value"]}'
            res = res + qs.replace('&', '?', 1)
        return setVars(res)

    @property
    def headers(self):
        headers = {}
        if not self.isAnonymous:
            headers.update({'Authorization': f'Bearer {Context.config["access_token"]}'})

        if 'header' in self.request:
            for header in self.request['header']:
                headers.update({header['key']: setVars(header['value'])})
        if 'body' in self.request:
            headers.update(getHeaderFromBody(self.request['body']))
        return headers

    @property
    def method(self):
        return self.request['method']

    @property
    def payload(self):
        if 'body' in self.request:
            if self.request['body']['mode'] == 'raw':
                return setVars(self.request['body']['raw'])

    def setToken(self, res):
        for event in self.events:
            if 'variable' in event:
                for var in event['variable']:
                    for key in var.keys():
                        expr = parse(var[key])
                        val = expr.find(res)
                        Context.config[key] = val[0].value if res is not None else None
