from gtmetrix import settings
import requests
import os.path
import time
import datetime


__all__ = ['GTmetrixInterface',
           'GTmetrixInvalidTestRequest',
           'GTmetrixTestNotFound',
           'GTmetrixMaximumNumberOfApis',
           'GTmetrixManyConcurrentRequests']


class GTmetrixInvalidTestRequest(Exception):
    """Invalid test request."""
    pass


class GTmetrixTestNotFound(Exception):
    """The requested test does not exist."""
    pass

class GTmetrixMaximumNumberOfApis(Exception):
    """The maximum number of API calls reached."""
    pass

class GTmetrixManyConcurrentRequests(Exception):
    """Too many concurrent requests from your IP."""
    pass

class _TestObject(object):
    """GTmetrix Test representation."""
    STATE_QUEUED = 'queued'
    STATE_STARTED = 'started'
    STATE_COMPLETED = 'completed'
    STATE_ERROR = 'error'

    def __init__(self, auth, test_id, poll_state_url=None):
        self.poll_state_url = (poll_state_url or
                               os.path.join(settings.GTMETRIX_REST_API_URL, test_id))
        self.test_id = test_id
        self.state = self.STATE_QUEUED
        self.auth = auth
        self.results = {}
        self.resources = {}
        self.pagespeed_score = {}
        self.yslow_score = {}
        self.html_bytes = {}
        self.html_load_time = {}
        self.page_bytes = {}
        self.page_load_time = {}
        self.page_elements ={}

    def _request(self, url):
        response = requests.get(url, auth=self.auth)
        response_data = response.json()

        if response.status_code == 404:
            raise GTmetrixTestNotFound(response_data['error'])

        if response.status_code == 400:
            raise GTmetrixInvalidTestRequest(response_data['error'])

        if response.status_code == 402:
            raise GTmetrixMaximumNumberOfApis(response_data['error'])

        if response.status_code == 429:
            raise GTmetrixManyConcurrentRequests(response_data['error'])

        return response_data

    def fetch_results(self, key):
        """Get the test state and results/resources (when test complete)."""
        response_data = self._request(self.poll_state_url)

        self.state = response_data['state']

        number_executions = 0
        while not self.state == self.STATE_COMPLETED and (number_executions < 30):
            number_executions += 1
            time.sleep(30)
            response_data = self._request(self.poll_state_url)
            self.state = response_data['state']

        self._extract_results(response_data, key)

        return response_data

    def _extract_results(self, response_data, key):
        self.results = response_data['results']
        self.pagespeed_score = self.results['pagespeed_score']
        self.yslow_score = self.results['yslow_score']
        self.html_bytes = self.results['html_bytes']
        self.html_load_time = self.results['html_load_time']
        self.page_bytes = self.results['page_bytes']
        self.page_load_time = self.results['page_load_time']
        self.page_elements = self.results['page_elements']

        today = datetime.datetime.now()
        day = today.day
        month = today.month
        year = today.year

        name_of_file = "results-%d-%d-%d" % (day,month, year)

        file = open(name_of_file, "a")
        file.write("site:%s pagespeed:%s yslow:%s tempo_carregamento:%s tamanho_pagina:%s total_elementos:%s \n" % (key, self.pagespeed_score, self.yslow_score, self.page_load_time, self.page_bytes, self.page_elements))
        file.close()


class GTmetrixInterface(object):
    """Provides an interface to access GTmetrix REST API."""
    def __init__(self, user_email, api_key):
        self.auth = (user_email, api_key)

    def start_test(self, url, **data):
        """ Start a Test """
        data.update({'url': url})
        response = requests.post(settings.GTMETRIX_REST_API_URL, data=data, auth=self.auth)
        response_data = response.json()

        if response.status_code != 200:
            raise GTmetrixInvalidTestRequest(response_data['error'])

        return _TestObject(self.auth, **response_data)

    def poll_state_request(self, key, test_id):
        test = _TestObject(self.auth, test_id)
        test.fetch_results(key)
        return test

