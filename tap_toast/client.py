
#
# Module dependencies.
#
import re
from datetime import timedelta
import backoff
import requests
import logging
import pytz
from tap_toast.context import Context
from tap_toast.postman import Postman

logger = logging.getLogger()
utc = pytz.UTC


def get_start_end_hour(start_date, end_date):
    delta = timedelta(hours=1)
    format_string = '%Y-%m-%dT%H:%M:%S.000-0000'  # hard coding this timezone because it's too complicated
    while start_date < end_date:
        yield start_date.strftime(format_string), (start_date + delta).strftime(format_string)
        start_date += delta


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


class Client(object):
    authentication = None

    def __init__(self):
        if 'authentication_postman' in Context.config:
            self.authentication = Postman(Context.config['authentication_postman'])

    @staticmethod
    def _url(path):
        return f'{Context.config["hostname"]}/{path.lstrip("/")}'

    @staticmethod
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

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException)
    def request(self, postman):
        if not postman.isAnonymous and not postman.is_authorized:
            self.get_authorization_token()

        payload = postman.payload
        headers = postman.headers
        url = postman.url

        logger.info(f'Request {postman.method} {url}')
        if postman.method == "GET":
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, headers=headers, json=payload)
        logger.info(f'{postman.method} request {url} response {response.status_code}')
        response.raise_for_status()
        self.readNextPage(postman, response)

        try:
            res = response.json()
            if isinstance(res, dict):
                res = [res]
        except ValueError as err:
            logger.error(f'HTTP error: {response.reason}')
            raise err

        return res

    def get_authorization_token(self):
        payload = self.authentication.payload
        headers = self.authentication.headers
        url = self.authentication.url
        logger.info(f'POST authentication request {url}')
        response = requests.post(url, data=payload, headers=headers)
        logger.info(f'POST authentication request {url} response {response.status_code}')
        response.raise_for_status()
        res = response.json()
        self.authentication.setToken(res)
        logger.info('Authorization successful.')
