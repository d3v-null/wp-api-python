# -*- coding: utf-8 -*-

"""
Wordpress API Class
"""

__title__ = "wordpress-api"

# from requests import request
from json import dumps as jsonencode
from wordpress.auth import OAuth, OAuth_3Leg, BasicAuth
from wordpress.transport import API_Requests_Wrapper
from wordpress.helpers import UrlUtils, StrUtils

class API(object):
    """ API Class """

    def __init__(self, url, consumer_key, consumer_secret, **kwargs):

        self.requester = API_Requests_Wrapper(url=url, **kwargs)

        auth_kwargs = dict(
            requester=self.requester,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
        )
        auth_kwargs.update(kwargs)

        if kwargs.get('basic_auth'):
            self.auth = BasicAuth(**auth_kwargs)
        else:
            if kwargs.get('oauth1a_3leg'):
                if 'callback' not in auth_kwargs:
                    raise TypeError("callback url not specified")
                self.auth = OAuth_3Leg( **auth_kwargs )
            else:
                self.auth = OAuth( **auth_kwargs )

    @property
    def url(self):
        return self.requester.url

    @property
    def timeout(self):
        return self.requester.timeout

    @property
    def namespace(self):
        return self.requester.api

    @property
    def version(self):
        return self.requester.api_version

    @property
    def verify_ssl(self):
        return self.requester.verify_ssl

    @property
    def is_ssl(self):
        return self.requester.is_ssl

    @property
    def consumer_key(self):
        return self.auth.consumer_key

    @property
    def consumer_secret(self):
        return self.auth.consumer_secret

    @property
    def callback(self):
        return self.auth.callback

    def request_post_mortem(self, response=None):
        """
        Attempt to diagnose what went wrong in a request
        """

        reason = None
        remedy = None

        response_json = {}
        try:
            response_json = response.json()
        except ValueError:
            pass

        # import pudb; pudb.set_trace()

        if 'code' in response_json or 'message' in response_json:
            reason = " - ".join([
                response_json.get(key) for key in ['code', 'message'] \
                if key in response_json
            ])

        request_body = {}
        request_url = ""
        if hasattr(response, 'request'):
            if hasattr(response.request, 'url'):
                request_url = response.request.url
            if hasattr(response.request, 'body'):
                request_body = response.request.body

        response_headers = {}
        if hasattr(response, 'headers'):
            response_headers = response.headers

        if not reason:
            requester_api_url = self.requester.api_url
            if hasattr(response, 'links') and response.links:
                links = response.links
                first_link_key = list(links)[0]
                header_api_url = links[first_link_key].get('url', '')
                if header_api_url:
                    header_api_url = StrUtils.eviscerate(header_api_url, '/')

                if header_api_url and requester_api_url\
                and header_api_url != requester_api_url:
                    reason = "hostname mismatch. %s != %s" % (
                        header_api_url, requester_api_url
                    )
                    header_url = StrUtils.eviscerate(header_api_url, '/')
                    header_url = StrUtils.eviscerate(header_url, self.requester.api)
                    header_url = StrUtils.eviscerate(header_url, '/')
                    remedy = "try changing url to %s" % header_url

        msg = "API call to %s returned \nCODE: %s\nRESPONSE:%s \nHEADERS: %s\nREQ_BODY:%s" % (
            request_url,
            str(response.status_code),
            UrlUtils.beautify_response(response),
            str(response_headers),
            str(request_body)
        )
        if reason:
            msg += "\nBecause of %s" % reason
        if remedy:
            msg += "\n%s" % remedy
        raise UserWarning(msg)

    def __request(self, method, endpoint, data):
        """ Do requests """

        endpoint_url = self.requester.endpoint_url(endpoint)
        endpoint_url = self.auth.get_auth_url(endpoint_url, method)
        auth = self.auth.get_auth()

        if data is not None:
            data = jsonencode(data, ensure_ascii=False).encode('utf-8')

        response = self.requester.request(
            method=method,
            url=endpoint_url,
            auth=auth,
            data=data
        )

        if response.status_code not in [200, 201]:
            self.request_post_mortem(response)

        return response

    def get(self, endpoint):
        """ Get requests """
        return self.__request("GET", endpoint, None)

    def post(self, endpoint, data):
        """ POST requests """
        return self.__request("POST", endpoint, data)

    def put(self, endpoint, data):
        """ PUT requests """
        return self.__request("PUT", endpoint, data)

    def delete(self, endpoint):
        """ DELETE requests """
        return self.__request("DELETE", endpoint, None)

    def options(self, endpoint):
        """ OPTIONS requests """
        return self.__request("OPTIONS", endpoint, None)
