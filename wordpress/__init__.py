# -*- coding: utf-8 -*-

"""
wordpress
~~~~~~~~~
A Python wrapper for Wordpress and WooCommerce REST APIs.

:copyright: (c) 2015 by WooThemes.
:license: MIT, see LICENSE for details.
"""

__title__ = "wordpress"
__version__ = "1.2.8"
__author__ = "Claudio Sanches @ WooThemes, forked by Derwent"
__license__ = "MIT"

__default_api_version__ = "wp/v2"
__default_api__ = "wp-json"

from wordpress.api import API
