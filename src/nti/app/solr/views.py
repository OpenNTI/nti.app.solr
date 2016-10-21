#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.event import notify

from zope.container.contained import Contained

from zope.traversing.interfaces import IPathAdapter

from nti.contentlibrary.interfaces import IContentUnit

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver import authorization as nauth

from nti.solr.interfaces import IndexObjectEvent

@interface.implementer(IPathAdapter)
class SOLRPathAdapter(Contained):

	__name__ = 'solr'

	def __init__(self, context, request):
		self.context = context
		self.request = request
		self.__parent__ = context

@view_config(name='solr_index')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=IContentUnit,
			   permission=nauth.ACT_NTI_ADMIN)
class IndexContentUnitView(AbstractAuthenticatedView):

	def __call__(self):
		notify(IndexObjectEvent(self.context))
		return hexc.HTTPNoContent()
