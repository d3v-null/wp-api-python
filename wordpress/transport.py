# -*- coding: utf-8 -*-

"""
Wordpress Requests Class
"""

__title__ = "wordpress-requests"

import logging
from json import dumps as jsonencode
from pprint import pformat

from requests import Request, Session
from wordpress import __default_api__, __default_api_version__, __version__
from wordpress.helpers import SeqUtils, StrUtils, UrlUtils

try:
    from urllib.parse import urlencode, quote, unquote, parse_qsl, urlparse, urlunparse
    from urllib.parse import ParseResult as URLParseResult
except ImportError:
    from urllib import urlencode, quote, unquote
    from urlparse import parse_qsl, urlparse, urlunparse
    from urlparse import ParseResult as URLParseResult


class API_Requests_Wrapper(object):
    """ provides a wrapper for making requests that handles session info """
    def __init__(self, url, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.url = url
        self.api = kwargs.get("api", __default_api__)
        self.api_version = kwargs.get("version", __default_api_version__)
        self.timeout = kwargs.get("timeout", 5)
        self.verify_ssl = kwargs.get("verify_ssl", True)
        self.session = Session()

    @property
    def is_ssl(self):
        return UrlUtils.is_ssl(self.url)

    @property
    def api_url(self):
        components = [
            self.url,
            self.api
        ]
        return UrlUtils.join_components(components)

    @property
    def api_ver_url(self):
        components = [
            self.url,
            self.api,
        ]
        if self.api_version != 'wp/v1':
            components += [
                self.api_version
            ]
        return UrlUtils.join_components(components)

    @property
    def api_ver_url_no_port(self):
        return UrlUtils.remove_port(self.api_ver_url)

    def endpoint_url(self, endpoint):
        endpoint = StrUtils.decapitate(endpoint, self.api_ver_url)
        endpoint = StrUtils.decapitate(endpoint, self.api_ver_url_no_port)
        endpoint = StrUtils.decapitate(endpoint, '/')
        components = [
            self.url,
            self.api
        ]
        if self.api_version != 'wp/v1':
            components += [
                self.api_version
            ]
        components += [
            endpoint
        ]
        return UrlUtils.join_components(components)

    def request(self, method, url, auth=None, params=None, data=None, **kwargs):
        headers = {
            "user-agent": "Wordpress API Client-Python/%s" % __version__,
            "accept": "application/json"
        }
        if data is not None:
            headers["content-type"] = "application/json;charset=utf-8"
        headers = SeqUtils.combine_ordered_dicts(
            headers,
            kwargs.get('headers', {})
        )

        request_kwargs = dict(
            method=method,
            url=url,
            headers=headers,
            verify=self.verify_ssl,
            timeout=self.timeout,
        )
        request_kwargs.update(kwargs)
        if auth is not None:
            request_kwargs['auth'] = auth
        if params is not None:
            request_kwargs['params'] = params
        if data is not None:
            request_kwargs['data'] = data
        self.logger.debug("request_kwargs:\n%s" % pformat([
            (key, repr(value)[:1000]) for key, value in request_kwargs.items()
        ]))
        response = self.session.request(
            **request_kwargs
        )
        self.logger.debug("response_code:\n%s" % pformat(response.status_code))
        try:
            response_json = response.json()
            self.logger.debug("response_json:\n%s" % (pformat(response_json)[:1000]))
        except ValueError:
            response_text = response.text
            self.logger.debug("response_text:\n%s" % (response_text[:1000]))
        response_headers = {}
        if hasattr(response, 'headers'):
            response_headers = response.headers
        self.logger.debug("response_headers:\n%s" % pformat(response_headers))
        response_links = {}
        if hasattr(response, 'links') and response.links:
            response_links = response.links
        self.logger.debug("response_links:\n%s" % pformat(response_links))





        return response

    def get(self, *args, **kwargs):
        return self.request("GET", *args, **kwargs)

    def post(self, *args, **kwargs):
        return self.request("POST", *args, **kwargs)
