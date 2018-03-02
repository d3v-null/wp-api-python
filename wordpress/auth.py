# -*- coding: utf-8 -*-

"""
Wordpress OAuth1.0a Class
"""

__title__ = "wordpress-auth"

# from base64 import b64encode
import binascii
import json
import logging
import os
from hashlib import sha1, sha256
from hmac import new as HMAC
from random import randint
from time import time
from pprint import pformat

# import webbrowser
import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth1

from bs4 import BeautifulSoup
from wordpress.helpers import UrlUtils

try:
    from urllib.parse import urlencode, quote, unquote, parse_qs, parse_qsl, urlparse, urlunparse
    from urllib.parse import ParseResult as URLParseResult
except ImportError:
    from urllib import urlencode, quote, unquote
    from urlparse import parse_qs, parse_qsl, urlparse, urlunparse
    from urlparse import ParseResult as URLParseResult

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict



class Auth(object):
    """ Boilerplate for handling authentication stuff. """

    def __init__(self, requester, **kwargs):
        self.requester = requester
        self.logger = logging.getLogger(__name__)
        self.query_string_auth = kwargs.pop('query_string_auth', True)

    @property
    def api_version(self):
        return self.requester.api_version

    @property
    def api_namespace(self):
        return self.requester.api

    def get_auth_url(self, endpoint_url, method):
        """ Returns the URL with added Auth params """
        return endpoint_url

    def get_auth(self):
        """ Returns the auth parameter used in requests """
        pass

class BasicAuth(Auth):
    """ Does not perform any signing, just logs in with oauth creds """
    def __init__(self, requester, consumer_key, consumer_secret, **kwargs):
        super(BasicAuth, self).__init__(requester, **kwargs)
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.user_auth = kwargs.pop('user_auth', None)
        self.wp_user = kwargs.pop('wp_user', None)
        self.wp_pass = kwargs.pop('wp_pass', None)

    def get_auth_url(self, endpoint_url, method, **kwargs):
        if self.query_string_auth:
            endpoint_params = UrlUtils.get_query_dict_singular(endpoint_url)
            endpoint_params.update({
                "consumer_key": self.consumer_key,
                "consumer_secret": self.consumer_secret
            })
            endpoint_url = UrlUtils.substitute_query(
                endpoint_url,
                UrlUtils.flatten_params(endpoint_params)
            )
        return endpoint_url

    def get_auth(self):
        if self.user_auth:
            return HTTPBasicAuth(self.wp_user, self.wp_pass)
        if not self.query_string_auth:
            return HTTPBasicAuth(self.consumer_key, self.consumer_secret)


class NoAuth(Auth):
    """
    Just a dummy Auth object to allow header based
    authorization per request
    """
    def get_auth_url(self, endpoint_url, method, **kwargs):
        return endpoint_url


class OAuth(Auth):
    """ Signs string with oauth consumer_key and consumer_secret """
    oauth_version = '1.0'
    force_nonce = None
    force_timestamp = None

    """ API Class """

    def __init__(self, requester, consumer_key, consumer_secret, **kwargs):
        super(OAuth, self).__init__(requester, **kwargs)
        if not self.query_string_auth:
            raise UserWarning("Header Auth not supported for OAuth")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.signature_method = kwargs.pop('signature_method', 'HMAC-SHA1')
        self.force_timestamp = kwargs.pop('force_timestamp', None)
        self.force_nonce = kwargs.pop('force_nonce', None)

    def get_sign_key(self, consumer_secret, token_secret=None):
        "gets consumer_secret and turns it into a bytestring suitable for signing"
        if not consumer_secret:
            raise UserWarning("no consumer_secret provided")
        token_secret = str(token_secret) if token_secret else ''
        if self.api_namespace == 'wc-api' \
        and self.api_version in ["v1", "v2"]:
            # special conditions for wc-api v1-2
            key = consumer_secret
        else:
            key = "%s&%s" % (consumer_secret, token_secret)
        return key

    def add_params_sign(self, method, url, params, sign_key=None, **kwargs):
        """ Adds the params to a given url, signs the url with sign_key if provided,
        otherwise generates sign_key automatically and returns a signed url """
        if isinstance(params, dict):
            params = list(params.items())

        urlparse_result = urlparse(url)

        if urlparse_result.query:
            params += parse_qsl(urlparse_result.query)
            # for key, value in parse_qsl(urlparse_result.query):
            #     params += [(key, value)]

        # headers = kwargs.get('headers', {})
        # if headers:
        #     params += headers.items()

        params = UrlUtils.unique_params(params)
        params = UrlUtils.sorted_params(params)

        params_without_signature = []
        for key, value in params:
            if key != "oauth_signature":
                params_without_signature.append((key, value))

        self.logger.debug('sorted_params before sign: %s' % pformat(params_without_signature) )

        signature = self.generate_oauth_signature(method, params_without_signature, url, sign_key)

        self.logger.debug('signature: %s' % signature )


        params = params_without_signature + [("oauth_signature", signature)]

        query_string = UrlUtils.flatten_params(params)

        return UrlUtils.substitute_query(url, query_string)

    def get_params(self):
        return [
            ("oauth_consumer_key", self.consumer_key),
            ("oauth_nonce", self.generate_nonce()),
            ("oauth_signature_method", self.signature_method),
            ("oauth_timestamp", self.generate_timestamp()),
        ]

    def get_auth_url(self, endpoint_url, method, **kwargs):
        """ Returns the URL with added Auth params """
        params = self.get_params()

        return self.add_params_sign(method, endpoint_url, params, **kwargs)

    @classmethod
    def get_signature_base_string(cls, method, params, url):
        # remove default port
        url = UrlUtils.remove_default_port(url)
        # ensure scheme is lowercase
        url = UrlUtils.lower_scheme(url)
        # remove query string parameters
        url = UrlUtils.substitute_query(url)
        base_request_uri = quote(url, "")
        query_string = UrlUtils.flatten_params(params)
        query_string = quote( query_string, '~')
        return "%s&%s&%s" % (
            method.upper(), base_request_uri, query_string
        )

    def generate_oauth_signature(self, method, params, url, key=None):
        """ Generate OAuth Signature """

        string_to_sign = self.get_signature_base_string(method, params, url)

        if key is None:
            key = self.get_sign_key(self.consumer_secret)

        if self.signature_method == 'HMAC-SHA1':
            hmac_mod = sha1
        elif self.signature_method == 'HMAC-SHA256':
            hmac_mod = sha256
        else:
            raise UserWarning("Unknown signature_method")

        # print "\nstring_to_sign: %s" % repr(string_to_sign)
        # print "\nkey: %s" % repr(key)
        sig = HMAC(
            bytes(key.encode('utf-8')),
            bytes(string_to_sign.encode('utf-8')),
            hmac_mod
        )
        sig_b64 = binascii.b2a_base64(sig.digest())[:-1]
        # print "\nsig_b64: %s" % sig_b64
        return sig_b64

    @classmethod
    def generate_timestamp(cls):
        """ Generate timestamp """
        if cls.force_timestamp is not None:
            return cls.force_timestamp
        return int(time())

    @classmethod
    def generate_nonce(cls):
        """ Generate nonce number """
        if cls.force_nonce is not None:
            return cls.force_nonce
        nonce = ''.join([str(randint(0, 9)) for i in range(8)])
        return HMAC(
            nonce.encode(),
            "secret".encode(),
            sha1
        ).hexdigest()

class OAuth_3Leg(OAuth):
    """ Provides 3 legged OAuth1a, mostly based off this: http://www.lexev.org/en/2015/oauth-step-step/"""

    # oauth_version = '1.0A'

    def __init__(self, requester, consumer_key, consumer_secret, callback, **kwargs):
        super(OAuth_3Leg, self).__init__(requester, consumer_key, consumer_secret, **kwargs)
        self.callback = callback
        self.wp_user = kwargs.pop('wp_user', None)
        self.wp_pass = kwargs.pop('wp_pass', None)
        self._creds_store = kwargs.pop('creds_store', None)
        self._authentication = None
        self._request_token = kwargs.pop('request_token', None)
        self.request_token_secret = None
        self._oauth_verifier = None
        self._access_token = kwargs.pop('access_token', None)
        self.access_token_secret = kwargs.pop('access_token_secret', None)

    @property
    def authentication(self):
        """ This is an object holding the authentication links discovered from the API
        automatically generated if accessed before generated """
        if not self._authentication:
            self._authentication = self.discover_auth()
        return self._authentication

    @property
    def oauth_verifier(self):
        """ This is the verifier string used in authentication
        automatically generated if accessed before generated """
        if not self._oauth_verifier:
            self._oauth_verifier = self.get_verifier()
        return self._oauth_verifier

    @property
    def request_token(self):
        """ This is the oauth_token used in requesting an access_token
        automatically generated if accessed before generated """
        if not self._request_token:
            self.get_request_token()
        return self._request_token

    @property
    def access_token(self):
        """ This is the oauth_token used to sign requests to protected resources
        automatically generated if accessed before generated """
        if not self._access_token and self.creds_store:
            self.retrieve_access_creds()
        if not self._access_token:
            self.get_access_token()
        return self._access_token

    @property
    def creds_store(self):
        if self._creds_store:
            return os.path.expanduser(self._creds_store)

    def get_auth_url(self, endpoint_url, method):
        """ Returns the URL with OAuth params """
        assert self.access_token, "need a valid access token for this step"
        assert self.access_token_secret, \
            "need a valid access token secret for this step"

        params = self.get_params()
        params += [
            ('oauth_callback', self.callback),
            ('oauth_token', self.access_token)
        ]

        sign_key = self.get_sign_key(self.consumer_secret, self.access_token_secret)

        self.logger.debug('sign_key: %s' % sign_key )

        return self.add_params_sign(method, endpoint_url, params, sign_key)

    def discover_auth(self):
        """ Discovers the location of authentication resourcers from the API"""
        discovery_url = self.requester.api_url

        response = self.requester.request('GET', discovery_url)
        response_json = response.json()

        has_authentication_resources = True

        if 'authentication' in response_json:
            authentication = response_json['authentication']
            if not isinstance(authentication, dict):
                has_authentication_resources = False
        else:
            has_authentication_resources = False

        if not has_authentication_resources:
            raise UserWarning(
                (
                    "Resopnse does not include location of authentication resources.\n"
                    "Resopnse: %s\n%s\n"
                    "Please check you have configured the Wordpress OAuth1 plugin correctly."
                ) % (response, response.text[:500])
            )

        self._authentication = authentication

        return self._authentication

    def get_request_token(self):
        """
        Uses the request authentication link to get an oauth_token for
        requesting an access token
        """

        assert self.consumer_key, "need a valid consumer_key for this step"

        params = self.get_params()
        params += [
            ('oauth_callback', self.callback)
        ]

        request_token_url = self.authentication['oauth1']['request']
        request_token_url = self.add_params_sign("GET", request_token_url, params)

        response = self.requester.get(request_token_url)
        self.logger.debug('get_request_token response: %s' % response.text)
        resp_content = parse_qs(response.text)

        try:
            self._request_token = resp_content['oauth_token'][0]
        except:
            raise UserWarning("Could not parse request_token in response from %s : %s" \
                % (repr(response.request.url), UrlUtils.beautify_response(response)))
        try:
            self.request_token_secret = resp_content['oauth_token_secret'][0]
        except:
            raise UserWarning("Could not parse request_token_secret in response from %s : %s" \
                % (repr(response.request.url), UrlUtils.beautify_response(response)))

        return self._request_token, self.request_token_secret

    def parse_login_form_error(self, response, exc, **kwargs):
        """
        If unable to parse login form, try to determine which error is present
        """
        login_form_soup = BeautifulSoup(response.text, 'lxml')
        if response.status_code == 500:
            error = login_form_soup.select_one('body#error-page')
            if error and error.stripped_strings:
                for stripped_string in error.stripped_strings:
                    if "plase solve this math problem" in stripped_string.lower():
                        raise UserWarning("Can't log in if form has capcha ... yet")
                raise UserWarning("could not parse login form error. %s " % str(error))
        if response.status_code == 200:
            error = login_form_soup.select_one('div#login_error')
            if error and error.stripped_strings:
                for stripped_string in error.stripped_strings:
                    if "invalid token" in stripped_string.lower():
                        raise UserWarning("Invalid token: %s" % repr(kwargs.get('token')))
                    elif "invalid username" in stripped_string.lower():
                        raise UserWarning("Invalid username: %s" % repr(kwargs.get('username')))
                    elif "the password you entered" in stripped_string.lower():
                        raise UserWarning("Invalid password: %s" % repr(kwargs.get('password')))
                raise UserWarning("could not parse login form error. %s " % str(error))
        raise UserWarning(
            "Login form response was code %s. original error: \n%s" % \
            (str(response.status_code), repr(exc))
        )

    def get_form_info(self, response, form_id):
        """ parses a form specified by a given form_id in the response,
        extracts form data and form action """

        assert \
            response.status_code is 200, \
            "login form response should be 200, not %s\n%s" % (
                response.status_code,
                response.text
            )
        response_soup = BeautifulSoup(response.text, "lxml")
        form_soup = response_soup.select_one('form#%s' % form_id)
        assert \
            form_soup, "unable to find form with id=%s in %s " \
            % (form_id, (response_soup.prettify()).encode('ascii', errors='backslashreplace'))
        # print "login form: \n", form_soup.prettify()

        action = form_soup.get('action')
        assert \
            action, "action should be provided by form: %s" \
            % (form_soup.prettify()).encode('ascii', errors='backslashreplace')

        form_data = OrderedDict()
        for input_soup in form_soup.select('input') + form_soup.select('button'):
            # print "input, class:%5s, id=%5s, name=%5s, value=%s" % (
            #     input_soup.get('class'),
            #     input_soup.get('id'),
            #     input_soup.get('name'),
            #     input_soup.get('value')
            # )
            name = input_soup.get('name')
            if not name:
                continue
            value = input_soup.get('value')
            if name not in form_data:
                form_data[name] = []
            form_data[name].append(value)

        # print "form data: %s" % str(form_data)
        return action, form_data

    def get_verifier(self, request_token=None, wp_user=None, wp_pass=None):
        """ pretends to be a browser, uses the authorize auth link, submits user creds to WP login form to get
        verifier string from access token """

        if request_token is None:
            request_token = self.request_token
        assert request_token, "need a valid request_token for this step"

        if wp_user is None and self.wp_user:
            wp_user = self.wp_user
        if wp_pass is None and self.wp_pass:
            wp_pass = self.wp_pass

        authorize_url = self.authentication['oauth1']['authorize']
        authorize_url = UrlUtils.add_query(authorize_url, 'oauth_token', request_token)

        # we're using a different session from the usual API calls
        # (I think the headers are incompatible?)

        # self.requester.get(authorize_url)
        authorize_session = requests.Session()

        login_form_response = authorize_session.get(authorize_url)
        login_form_params = {
            'username':wp_user,
            'password':wp_pass,
            'token':request_token
        }
        try:
            login_form_action, login_form_data = self.get_form_info(login_form_response, 'loginform')
        except AssertionError as exc:
            self.parse_login_form_error(
                login_form_response, exc, **login_form_params
            )

        for name, values in login_form_data.items():
            if name == 'log':
                login_form_data[name] = wp_user
            elif name == 'pwd':
                login_form_data[name] = wp_pass
            else:
                login_form_data[name] = values[0]

        assert 'log' in login_form_data, 'input for user login did not appear on form'
        assert 'pwd' in login_form_data, 'input for user password did not appear on form'

        # print "submitting login form to %s : %s" % (login_form_action, str(login_form_data))

        confirmation_response = authorize_session.post(login_form_action, data=login_form_data, allow_redirects=True)
        try:
            authorize_form_action, authorize_form_data = self.get_form_info(confirmation_response, 'oauth1_authorize_form')
        except AssertionError as exc:
            self.parse_login_form_error(
                confirmation_response, exc, **login_form_params
            )

        for name, values in authorize_form_data.items():
            if name == 'wp-submit':
                assert \
                    'authorize' in values, \
                    "apparently no authorize button, only %s" % str(values)
                authorize_form_data[name] = 'authorize'
            else:
                authorize_form_data[name] = values[0]

        assert 'wp-submit' in login_form_data, 'authorize button did not appear on form'

        final_response = authorize_session.post(authorize_form_action, data=authorize_form_data, allow_redirects=False)

        assert \
            final_response.status_code == 302, \
            "was not redirected by authorize screen, was %d instead. something went wrong" \
                % final_response.status_code
        assert 'location' in final_response.headers, "redirect did not provide redirect location in header"

        final_location = final_response.headers['location']

        # At this point we can chose to follow the redirect if the user wants,
        # or just parse the verifier out of the redirect url.
        # open to suggestions if anyone has any :)

        final_location_queries = parse_qs(urlparse(final_location).query)

        assert \
            'oauth_verifier' in final_location_queries, \
            "oauth verifier not provided in final redirect: %s" % final_location

        self._oauth_verifier = final_location_queries['oauth_verifier'][0]
        return self._oauth_verifier

    def store_access_creds(self):
        """ store the access_token and access_token_secret locally. """

        if not self.creds_store:
            return

        creds = OrderedDict()
        if self._access_token:
            creds['access_token'] = self._access_token
        if self.access_token_secret:
            creds['access_token_secret'] = self.access_token_secret
        if creds:
            with open(self.creds_store, 'w+') as creds_store_file:
                json.dump(creds, creds_store_file, ensure_ascii=False)

    def retrieve_access_creds(self):
        """ retrieve the access_token and access_token_secret stored locally. """

        if not self.creds_store:
            return

        creds = {}
        if os.path.isfile(self.creds_store):
            with open(self.creds_store, 'r') as creds_store_file:
                try:
                    creds = json.load(creds_store_file, encoding='utf-8')
                except ValueError:
                    pass

        if 'access_token' in creds:
            self._access_token = creds['access_token']
        if 'access_token_secret' in creds:
            self.access_token_secret = creds['access_token_secret']

    def clear_stored_creds(self):
        """ Clear the file containing stored creds. """

        if not self.creds_store:
            return

        with open(self.creds_store, 'w+') as creds_store_file:
            creds_store_file.write('')


    def get_access_token(self, oauth_verifier=None):
        """ Uses the access authentication link to get an access token """

        if oauth_verifier is None:
            oauth_verifier = self.oauth_verifier
        assert oauth_verifier, "Need an oauth verifier to perform this step"
        assert self.request_token, "Need a valid request_token to perform this step"

        params = self.get_params()
        params += [
            ('oauth_token', self.request_token),
            ('oauth_verifier', self.oauth_verifier)
        ]

        sign_key = self.get_sign_key(self.consumer_secret, self.request_token_secret)

        access_token_url = self.authentication['oauth1']['access']
        access_token_url = self.add_params_sign("POST", access_token_url, params, sign_key)

        access_response = self.requester.post(access_token_url)

        self.logger.debug('access_token response: %s' % access_response.text)

        assert \
            access_response.status_code == 200, \
            "Access request did not return 200, returned %s. HTML: %s" % (
                access_response.status_code,
                UrlUtils.beautify_response(access_response)
            )

        #
        access_response_queries = parse_qs(access_response.text)

        try:
            self._access_token = access_response_queries['oauth_token'][0]
            self.access_token_secret = access_response_queries['oauth_token_secret'][0]
        except:
            raise UserWarning("Could not parse access_token or access_token_secret in response from %s : %s" \
                % (repr(access_response.request.url), UrlUtils.beautify_response(access_response)))

        self.store_access_creds()

        return self._access_token, self.access_token_secret
