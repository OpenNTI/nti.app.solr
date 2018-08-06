#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from requests.structures import CaseInsensitiveDict

import six

from zope.event import notify

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.externalization.error import raise_json_error

from nti.app.externalization.view_mixins import ModeledContentUploadRequestUtilsMixin

from nti.app.solr.views import all_usernames
from nti.app.solr.views import username_search

from nti.app.solr.views import SOLRPathAdapter

from nti.contenttypes.presentation.interfaces import INTIMedia
from nti.contenttypes.presentation.interfaces import INTITranscript
from nti.contenttypes.presentation.interfaces import INTIDocketAsset

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import ICommunity
from nti.dataserver.interfaces import IFriendsList
from nti.dataserver.interfaces import IUserGeneratedData

from nti.dataserver.users.users import User

from nti.externalization.proxy import removeAllProxies

from nti.solr.interfaces import IndexObjectEvent
from nti.solr.interfaces import UnindexObjectEvent

from nti.solr.utils import object_finder

logger = __import__('logging').getLogger(__name__)


def solr_notify(context):
    context = removeAllProxies(context)
    notify(IndexObjectEvent(context))


@view_config(name='index')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class SOLRIndexObjectView(AbstractAuthenticatedView):

    def _notify(self, context):
        solr_notify(context)

    def __call__(self):
        request = self.request
        uid = request.subpath[0] if request.subpath else None
        if uid is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': u"Must specify an object id."
                             },
                             None)
        context = object_finder(uid)
        if context is None:
            raise hexc.HTTPNotFound()
        self._notify(context)
        return hexc.HTTPNoContent()


@view_config(name='unindex')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class UnindexSOLRObjectView(AbstractAuthenticatedView):

    def _notify(self, context):
        context = removeAllProxies(context)
        notify(UnindexObjectEvent(context))

    def __call__(self):
        request = self.request
        uid = request.subpath[0] if request.subpath else None
        if uid is None:
            raise_json_error(self.request,
                             hexc.HTTPUnprocessableEntity,
                             {
                                 'message': u"Must specify an object id."
                             },
                             None)
        context = object_finder(uid)
        if context is None:
            raise hexc.HTTPNotFound()
        self._notify(context)
        return hexc.HTTPNoContent()


@view_config(context=IUser)
@view_config(context=INTIMedia)
@view_config(context=INTITranscript)
@view_config(context=INTIDocketAsset)
@view_config(context=IUserGeneratedData)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_index',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class IndexObjectView(SOLRIndexObjectView):

    def __call__(self):
        self._notify(self.context)
        return hexc.HTTPNoContent()


@view_config(context=IUser)
@view_config(context=INTIMedia)
@view_config(context=INTITranscript)
@view_config(context=INTIDocketAsset)
@view_config(context=IUserGeneratedData)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_unindex',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class UnindexObjectView(UnindexSOLRObjectView):

    def __call__(self):
        self._notify(self.context)
        return hexc.HTTPNoContent()


@view_config(context=ICommunity)
@view_config(context=IFriendsList)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_index',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class IndexMembershipObjectView(SOLRIndexObjectView):

    def __call__(self):
        self._notify(self.context)
        for user in self.context:  # pylint: disable=not-an-iterable
            self._notify(user)
        return hexc.HTTPNoContent()


@view_config(context=ICommunity)
@view_config(context=IFriendsList)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_unindex',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class UnindexMembershipObjectView(UnindexSOLRObjectView):

    def __call__(self):
        self._notify(self.context)
        for user in self.context:  # pylint: disable=not-an-iterable
            self._notify(user)
        return hexc.HTTPNoContent()


@view_config(name='IndexUsers')
@view_config(name='index_users')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               context=SOLRPathAdapter,
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class IndexUsersViews(SOLRIndexObjectView,
                      ModeledContentUploadRequestUtilsMixin):

    def readInput(self, value=None):
        if self.request.body:
            values = super(IndexUsersViews, self).readInput(value)
        else:
            values = {}
        return CaseInsensitiveDict(values)

    def __call__(self):
        values = self.readInput()
        term = values.get('term') or values.get('search')
        usernames = values.get('usernames') or values.get('username')
        if term:
            usernames = username_search(term)
        elif isinstance(usernames, six.string_types):
            usernames = set(usernames.split(","))
        else:
            usernames = all_usernames()
        for name in usernames or ():
            user = User.get_user(name)
            if IUser.providedBy(user):
                self._notify(user)
        return hexc.HTTPNoContent()
