import os
import re


def get_abs_path(path, base=None):
    if base is None:
        base = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(base, path)


def readNextPage(postman, response):
    has_next = False
    if 'link' in response.headers:
        links = response.headers['link'].split(',')
        for link in links:
            groups = re.findall(r'^ ?<(.*)>; ?rel="next"$', link)
            if groups:
                postman.setUrl(groups[0])
                has_next = True
    if not has_next:
        postman.request = None
