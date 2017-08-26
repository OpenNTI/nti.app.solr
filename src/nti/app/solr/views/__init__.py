#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import six

from zope import component
from zope import interface

from zope.location.interfaces import IContained

from zope.traversing.interfaces import IPathAdapter

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout


@interface.implementer(IPathAdapter, IContained)
class SOLRPathAdapter(object):

    __name__ = 'solr'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context


def _make_min_max_btree_range(search_term):
    min_inclusive = search_term  # start here
    max_exclusive = search_term[0:-1] + six.unichr(ord(search_term[-1]) + 1)
    return min_inclusive, max_exclusive


def username_search(search_term):
    min_inclusive, max_exclusive = _make_min_max_btree_range(search_term)
    dataserver = component.getUtility(IDataserver)
    _users = IShardLayout(dataserver).users_folder
    usernames = _users.iterkeys(min_inclusive, max_exclusive, excludemax=True)
    return usernames


def all_usernames():
    dataserver = component.getUtility(IDataserver)
    users_folder = IShardLayout(dataserver).users_folder
    usernames = users_folder.keys()
    return usernames
