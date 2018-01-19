# -*- coding: utf-8 -*-

"""
Wordpress Hellpers Class
"""

__title__ = "wordpress-requests"

import re

import posixpath

from functools import reduce

try:
    from urllib.parse import urlencode, quote, unquote, parse_qsl, urlparse, urlunparse
    from urllib.parse import ParseResult as URLParseResult
except ImportError:
    from urllib import urlencode, quote, unquote
    from urlparse import parse_qs, parse_qsl, urlparse, urlunparse
    from urlparse import ParseResult as URLParseResult

from collections import OrderedDict

from bs4 import BeautifulSoup


class StrUtils(object):
    @classmethod
    def remove_tail(cls, string, tail):
        if string.endswith(tail):
            string = string[:-len(tail)]
        return string

    @classmethod
    def remove_head(cls, string, head):
        if string.startswith(head):
            string = string[len(head):]
        return string

    @classmethod
    def decapitate(cls, *args, **kwargs):
        return cls.remove_head(*args, **kwargs)

    @classmethod
    def eviscerate(cls, *args, **kwargs):
        return cls.remove_tail(*args, **kwargs)


class SeqUtils(object):
    @classmethod
    def filter_true(cls, seq):
        return [item for item in seq if item]


    @classmethod
    def filter_unique_true(cls, list_a):
        response = []
        for i in list_a:
            if i and i not in response:
                response.append(i)
        return response

    @classmethod
    def combine_two_ordered_dicts(cls, dict_a, dict_b):
        """
        Combine OrderedDict a with b by starting with A and overwriting with items from b.
        Attempt to preserve order
        """
        if not dict_a:
            return dict_b if dict_b else OrderedDict()
        if not dict_b:
            return dict_a
        response = OrderedDict(dict_a.items())
        for key, value in dict_b.items():
            response[key] = value
        return response

    @classmethod
    def combine_ordered_dicts(cls, *args):
        """
        Combine all dict arguments overwriting former with items from latter.
        Attempt to preserve order
        """
        response = OrderedDict()
        for arg in args:
            response = cls.combine_two_ordered_dicts(response, arg)
        return response

class UrlUtils(object):

    reg_netloc = r'(?P<hostname>[^:]+)(:(?P<port>\d+))?'

    @classmethod
    def get_query_list(cls, url):
        """ returns the list of queries in the url """
        return parse_qsl(urlparse(url).query)

    @classmethod
    def get_query_dict_singular(cls, url):
        """ return an ordered mapping from each key in the query string to a singular value """
        query_list = cls.get_query_list(url)
        return OrderedDict(query_list)
        # query_dict = parse_qs(urlparse(url).query)
        # query_dict_singular = dict([
        #     (key, value[0]) for key, value in query_dict.items()
        # ])
        # return query_dict_singular

    @classmethod
    def set_query_singular(cls, url, key, value):
        """ Sets or overrides a single query in a url """
        query_dict_singular = cls.get_query_dict_singular(url)
        # print "setting key %s to value %s" % (key, value)
        query_dict_singular[key] = value
        # print query_dict_singular
        query_string = urlencode(query_dict_singular)
        # print "new query string", query_string
        return cls.substitute_query(url, query_string)

    @classmethod
    def get_query_singular(cls, url, key, default=None):
        """ Gets the value of a single query in a url """
        url_params = parse_qs(urlparse(url).query)
        values = url_params.get(key, [default])
        assert len(values) == 1, "ambiguous value, could not get singular for key: %s" % key
        return values[0]

    @classmethod
    def del_query_singular(cls, url, key):
        """ deletes a singular key from the query string """
        query_dict_singular = cls.get_query_dict_singular(url)
        if key in query_dict_singular:
            del query_dict_singular[key]
            query_string = urlencode(query_dict_singular)
            url = cls.substitute_query(url, query_string)
        return url

    # @classmethod
    # def split_url_query(cls, url):
    #     """ Splits a url, returning the url without query and the query as a dict """
    #     parsed_result = urlparse(url)
    #     parsed_query_dict = parse_qs(parsed_result.query)
    #     split_url = cls.substitute_query(url)
    #     return split_url, parsed_query_dict

    @classmethod
    def split_url_query_singular(cls, url):
        query_dict_singular = cls.get_query_dict_singular(url)
        split_url = cls.substitute_query(url)
        return split_url, query_dict_singular

    @classmethod
    def substitute_query(cls, url, query_string=None):
        """ Replaces the query string in the url with the provided string or
        removes the query string if none is provided """
        if not query_string:
            query_string = ''

        urlparse_result = urlparse(url)

        return urlunparse(URLParseResult(
            scheme=urlparse_result.scheme,
            netloc=urlparse_result.netloc,
            path=urlparse_result.path,
            params=urlparse_result.params,
            query=query_string,
            fragment=urlparse_result.fragment
        ))

    @classmethod
    def add_query(cls, url, new_key, new_value):
        """ adds a query parameter to the given url """
        new_query_item = '%s=%s' % (quote(str(new_key)), quote(str(new_value)))
        # new_query_item = '='.join([quote(new_key), quote(new_value)])
        new_query_string = "&".join(SeqUtils.filter_true([
            urlparse(url).query,
            new_query_item
        ]))
        return cls.substitute_query(url, new_query_string)

    @classmethod
    def is_ssl(cls, url):
        return urlparse(url).scheme == 'https'

    @classmethod
    def join_components(cls, components):
        return reduce(posixpath.join, SeqUtils.filter_true(components))

    @staticmethod
    def get_value_like_as_php(val):
        """ Prepare value for quote """
        try:
            base = basestring
        except NameError:
            base = (str, bytes)

        if isinstance(val, base):
            return val
        elif isinstance(val, bool):
            return "1" if val else ""
        elif isinstance(val, int):
            return str(val)
        elif isinstance(val, float):
            return str(int(val)) if val % 1 == 0 else str(val)
        else:
            return ""

    @staticmethod
    def beautify_response(response):
        """ Returns a beautified response in the default locale """
        return BeautifulSoup(response.text, 'lxml').prettify().encode(errors='backslashreplace')

    @classmethod
    def remove_port(cls, url):
        """ Remove the port number from a URL"""

        urlparse_result = urlparse(url)

        return urlunparse(URLParseResult(
            scheme=urlparse_result.scheme,
            netloc=re.sub(r':\d+', r'', urlparse_result.netloc),
            path=urlparse_result.path,
            params=urlparse_result.params,
            query=urlparse_result.query,
            fragment=urlparse_result.fragment
        ))

    @classmethod
    def remove_default_port(cls, url, defaults=None):
        """ Remove the port number from a URL if it is a default port. """
        if defaults is None:
            defaults = {
                'http':80,
                'https':443
            }

        urlparse_result = urlparse(url)
        match = re.match(
            cls.reg_netloc,
            urlparse_result.netloc
        )
        assert match, "netloc %s should match regex %s"
        if match.groupdict().get('port'):
            hostname = match.groupdict()['hostname']
            port = int(match.groupdict()['port'])
            scheme = urlparse_result.scheme.lower()

            if defaults[scheme] == port:
                return urlunparse(URLParseResult(
                    scheme=urlparse_result.scheme,
                    netloc=hostname,
                    path=urlparse_result.path,
                    params=urlparse_result.params,
                    query=urlparse_result.query,
                    fragment=urlparse_result.fragment
                ))
        return urlunparse(URLParseResult(
            scheme=urlparse_result.scheme,
            netloc=urlparse_result.netloc,
            path=urlparse_result.path,
            params=urlparse_result.params,
            query=urlparse_result.query,
            fragment=urlparse_result.fragment
        ))

    @classmethod
    def lower_scheme(cls, url):
        """ ensure the scheme of the url is lowercase. """
        urlparse_result = urlparse(url)
        return urlunparse(URLParseResult(
            scheme=urlparse_result.scheme.lower(),
            netloc=urlparse_result.netloc,
            path=urlparse_result.path,
            params=urlparse_result.params,
            query=urlparse_result.query,
            fragment=urlparse_result.fragment
        ))

    @classmethod
    def normalize_str(cls, string):
        """ Normalize string for the purposes of url query parameters. """
        return quote(string, '~')

    @classmethod
    def normalize_params(cls, params):
        """ Normalize parameters. works with RFC 5849 logic. params is a list of key, value pairs """
        if isinstance(params, dict):
            params = params.items()
        params = [
            (
                cls.normalize_str(key),
                cls.normalize_str(UrlUtils.get_value_like_as_php(value))
            ) for key, value in params
        ]

        response = params
        return response

    @classmethod
    def sorted_params(cls, params):
        """ Sort parameters. works with RFC 5849 logic. params is a list of key, value pairs """

        if isinstance(params, dict):
            params = params.items()

        if not params:
            return params
        # return sorted(params)
        ordered = []
        params_sorting = []
        for i, (key, value) in enumerate(params):
            base_key = key.split('[')[0]
            params_sorting.append((base_key, value, i, key))

        for _, value, _, key in sorted(params_sorting):
            ordered.append((key, value))

        return ordered

    @classmethod
    def unique_params(cls, params):
        if isinstance(params, dict):
            params = params.items()

        if not params:
            return params

        unique_params = []
        seen_keys = []
        for key, value in params:
            if key not in seen_keys:
                unique_params.append((key, value))
                seen_keys.append(key)
        return unique_params

    @classmethod
    def flatten_params(cls, params):
        if isinstance(params, dict):
            params = params.items()
        params = cls.normalize_params(params)
        params = cls.sorted_params(params)
        params = cls.unique_params(params)
        return "&".join(["%s=%s"%(key, value) for key, value in params])
