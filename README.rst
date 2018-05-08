Wordpress API - Python Client
===============================

A Python wrapper for the Wordpress and WooCommerce REST APIs with oAuth1a 3leg support.

Supports the Wordpress REST API v1-2, WooCommerce REST API v1-3 and WooCommerce WP-API v1-2 (with automatic OAuth3a handling).
Forked from the excellent WooCommerce API written by Claudio Sanches and modified to work with Wordpress: https://github.com/woocommerce/wc-api-python

I created this fork because I prefer the way that the wc-api-python client interfaces with
the Wordpress API compared to the existing python client, https://pypi.python.org/pypi/wordpress_json
which does not support OAuth authentication, only Basic Authentication (very unsecure)

Any comments about how you're using the API and suggestions about how this repository could be improved are welcome :).
You can find my contact info in my GitHub profile.

Roadmap
-------

- [x] Create initial fork
- [x] Implement 3-legged OAuth on Wordpress client
- [x] Better local storage of OAuth credentials to stop unnecessary API keys being generated
- [x] Support image upload to WC Api
- [ ] Better handling of timeouts with a back-off
- [ ] Implement iterator for convenient access to API items

Requirements
------------

Wordpress version 4.7+ comes pre-installed with REST API v2, so you don't need to have the WP REST API plugin if you have the latest Wordpress.

You should have the following plugins installed on your wordpress site:

- **WP REST API** (only required for WP < v4.7, recommended version: 2.0+)
- **WP REST API - OAuth 1.0a Server** (optional, if you want oauth within the wordpress API. https://github.com/WP-API/OAuth1)
- **WP REST API - Meta Endpoints** (optional)
- **WooCommerce** (optional, if you want to use the WooCommerce API)

The following python packages are also used by the package

- **requests**
- **beautifulsoup**

Installation
------------

Install with pip

.. code-block:: bash

    pip install wordpress-api

Download this repo and use setuptools to install the package

.. code-block:: bash

    pip install setuptools
    git clone https://github.com/derwentx/wp-api-python
    python setup.py install

Testing
-------

If you have installed from source, then you can test with unittest:

.. code-block:: bash

    pip install -r requirements-test.txt
    py.test --cov=wordpress tests.py

Getting started
---------------

Generate API credentials (Consumer Key & Consumer Secret) following these instructions: http://v2.wp-api.org/guide/authentication/

Simply go to Users -> Applications and create an Application, e.g. "REST API".
Enter a callback URL that you will be able to remember later such as "http://example.com/oauth1_callback" (not really important for this client).
Store the resulting Key and Secret somewhere safe.

Check out the Wordpress API endpoints and data that can be manipulated in http://v2.wp-api.org/reference/.

Setup
-----

Wordpress API with Basic authentication:
----
(Note: requires Basic Authentication plugin)

.. code-block:: python

    from wordpress import API

    wpapi = API(
        url="http://example.com",
        api="wp-json",
        version='wp/v2',
        wp_user="XXXX",
        wp_pass="XXXX",
        basic_auth = True,
        user_auth = True,
    )

WP REST API v2:
----
(Note: the username and password are required so that it can fill out the oauth request token form automatically for you.
Requires OAuth 1.0a plugin. )

.. code-block:: python

    #...

    wpapi = API(
        url="http://example.com",
        consumer_key="XXXXXXXXXXXX",
        consumer_secret="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        api="wp-json",
        version="wp/v2",
        wp_user="XXXX",
        wp_pass="XXXX",
        oauth1a_3leg=True,
        creds_store="~/.wc-api-creds.json"
    )

Legacy WooCommerce API v3:
----

.. code-block:: python

    #...

    wcapi = API(
        url="http://example.com",
        consumer_key="ck_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        consumer_secret="cs_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        api="wc-api",
        version="v3"
    )

New WC REST API:
----
Note: oauth1a 3legged works with Wordpress but not with WooCommerce. However oauth1a signing still works.
If you try to do oauth1a_3leg with WooCommerce it just says "consumer_key not valid", even if it is valid.

.. code-block:: python

    #...

    wcapi = API(
        url="http://example.com",
        consumer_key="ck_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        consumer_secret="cs_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        api="wp-json",
        version="wc/v2",
        callback='http://127.0.0.1/oauth1_callback'
    )


Options
~~~~~~~

+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
|         Option        |     Type    | Required |                                              Description                                                         |
+=======================+=============+==========+==================================================================================================================+
| ``url``               | ``string``  | yes      | Your Store URL, example: http://wp.dev/                                                                          |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``consumerKey``       | ``string``  | yes      | Your API consumer key                                                                                            |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``consumerSecret``    | ``string``  | yes      | Your API consumer secret                                                                                         |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``api``               | ``string``  | no       | Determines which api to use, defaults to ``wp-json``, can be arbitrary: ``wc-api``, ``oembed``                   |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``version``           | ``string``  | no       | API version, default is ``wp/v2``, can be ``v3`` or  ``wc/v1`` if using ``wc-api``                               |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``timeout``           | ``integer`` | no       | Connection timeout, default is ``5``                                                                             |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``verify_ssl``        | ``bool``    | no       | Verify SSL when connect, use this option as ``False`` when need to test with self-signed certificates            |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``basic_auth``        | ``bool``    | no       | Force Basic Authentication, can be through query string or headers (default)                                     |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``query_string_auth`` | ``bool``    | no       | Use query string for Basic Authentication when ``True`` and using HTTPS, default is ``False`` which uses header  |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``oauth1a_3leg``      | ``string``  | no       | use oauth1a 3-legged authentication                                                                              |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+
| ``creds_store``       | ``string``  | no       | JSON file where oauth verifier is stored (only used with OAuth_3Leg)                                             |
+-----------------------+-------------+----------+------------------------------------------------------------------------------------------------------------------+

Methods
-------

+--------------+----------------+------------------------------------------------------------------+
|    Params    |      Type      |                           Description                            |
+==============+================+==================================================================+
| ``endpoint`` | ``string``     | API endpoint, example: ``posts`` or ``user/12``                  |
+--------------+----------------+------------------------------------------------------------------+
| ``data``     | ``dictionary`` | Data that will be converted to JSON                              |
+--------------+----------------+------------------------------------------------------------------+

GET
~~~

- ``.get(endpoint)``

POST
~~~~

- ``.post(endpoint, data)``

PUT
~~~

- ``.put(endpoint, data)``

DELETE
~~~~~~

- ``.delete(endpoint)``

OPTIONS
~~~~~~~

- ``.options(endpoint)``

Upload an image
-----

(Note: this only works on WP API with basic auth)

.. code-block:: python

    assert os.path.exists(img_path), "img should exist"
    data = open(img_path, 'rb').read()
    filename = os.path.basename(img_path)
    _, extension = os.path.splitext(filename)
    headers = {
        'cache-control': 'no-cache',
        'content-disposition': 'attachment; filename=%s' % filename,
        'content-type': 'image/%s' % extension
    }
    return wcapi.post(self.endpoint_singular, data, headers=headers)


Response
--------

All methods will return `Response <http://docs.python-requests.org/en/latest/api/#requests.Response>`_ object.

Example of returned data:

.. code-block:: bash

    >>> from wordpress import api as wpapi
    >>> r = wpapi.get("posts")
    >>> r.status_code
    200
    >>> r.headers['content-type']
    'application/json; charset=UTF-8'
    >>> r.encoding
    'UTF-8'
    >>> r.text
    u'{"posts":[{"title":"Flying Ninja","id":70,...' // Json text
    >>> r.json()
    {u'posts': [{u'sold_individually': False,... // Dictionary data

A note on DELETE requests.
=====

The extra keyword arguments passed to the function of a `__request` call (such as `.delete()`) to a `wordpress.API` object are used to modify a `Requests.request` call, this is to allow you to specify custom parameters to modify how the request is made such as `headers`. At the moment it only passes the `headers` parameter to requests, but if I see a use case for it, I can forward more of the parameters to `Requests`.
The `delete` function doesn’t accept a data object because a HTTP DELETE request does not typically have a payload, and some implementations of a HTTP server would reject a DELETE request that has a payload.
You can still pass api request parameters in the query string of the URL. I would suggest using a library like `urlparse` / `urllib.parse` to modify the query string if you are automatically deleting users.
According the the [documentation](https://developer.wordpress.org/rest-api/reference/users/#delete-a-user) for deleting a user, you need to pass the `force` and `reassign` parameters to the API, which can be done by appending them to the endpoint URL.
.. code-block:: python
    >>> response = wpapi.delete(‘/users/<Id>?reassign=<other_id>&force=true’)
    >>> response.json()
    {“deleted”:true, ... }


Changelog
---------

1.2.6 - 2018/01/29
~~~~~~~~~~~~~~~~~~
- Better Python3 support
- Tested on Python v3.6.2 and v2.7.13

1.2.5 - 2017/12/07
~~~~~~~~~~~~~~~~~~
- Better UTF-8 support

1.2.4 - 2017/10/01
~~~~~~~~~~~~~~~~~~
- Support for image upload
- More accurate documentation of WP authentication methods

1.2.3 - 2017/09/07
~~~~~~~~~~~~~~~~~~
- Better local storage of OAuth creds to stop unnecessary API keys being generated
- Improve parsing of API errors to display much more useful error information

1.2.2 - 2017/06/16
~~~~~~~~~~~~~~~~~~
- support basic auth without https
- rename oauth module to auth (since auth covers oauth and basic auth)
- tested with latest versions of WP and WC

1.2.1 - 2016/12/13
~~~~~~~~~~~~~~~~~~
- tested to handle complex queries like filter[limit]
- fix: Some edge cases where queries were out of order causing signature mismatch
- hardened helper and api classes and added corresponding test cases

1.2.0 - 2016/09/28
~~~~~~~~~~~~~~~~~~

- Initial fork
- Implemented 3-legged OAuth
- Tested with pagination
