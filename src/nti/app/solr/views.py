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

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.dataserver import authorization as nauth

from nti.externalization.proxy import removeAllProxies

from nti.solr.interfaces import IndexObjectEvent

from nti.solr.utils import object_finder

@interface.implementer(IPathAdapter)
class SOLRPathAdapter(Contained):

	__name__ = 'solr'

	def __init__(self, context, request):
		self.context = context
		self.request = request
		self.__parent__ = context

@view_config(name='index')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=SOLRPathAdapter,
			   permission=nauth.ACT_NTI_ADMIN)
class IndexObjectView(AbstractAuthenticatedView):

	def _notify(self, context):
		context = removeAllProxies(context)
		notify(IndexObjectEvent(context))

	def __call__(self):
		request = self.request
		uid = request.subpath[0] if request.subpath else ''
		if uid is None:
			raise hexc.HTTPUnprocessableEntity("Must specify an object id")
		context = object_finder(uid)
		if context is None:
			raise hexc.HTTPNotFound()
		self._notify(context)
		return hexc.HTTPNoContent()

@view_config(name='solr_index')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=IContentUnit,
			   permission=nauth.ACT_NTI_ADMIN)
class IndexContentUnitView(IndexObjectView):

	def __call__(self):
		self._notify(self.context)
		return hexc.HTTPNoContent()

@view_config(context=ICourseInstance)
@view_config(context=ICourseCatalogEntry)
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   name='solr_index',
			   request_method='POST',
			   permission=nauth.ACT_NTI_ADMIN)
class IndexCourseView(IndexObjectView):

	def __call__(self):
		self._notify(ICourseInstance(self.context))
		return hexc.HTTPNoContent()
