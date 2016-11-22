#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.event import notify

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.solr.views import SOLRPathAdapter

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IGlobalContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.contenttypes.presentation.interfaces import INTIMedia 
from nti.contenttypes.presentation.interfaces import INTITranscript 
from nti.contenttypes.presentation.interfaces import INTIDocketAsset

from nti.dataserver import authorization as nauth

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserGeneratedData

from nti.externalization.proxy import removeAllProxies

from nti.solr import QUEUE_NAMES

from nti.solr.common import get_job_queue

from nti.solr.interfaces import IndexObjectEvent
from nti.solr.interfaces import UnindexObjectEvent

from nti.solr.utils import object_finder

@view_config(name='index')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=SOLRPathAdapter,
			   permission=nauth.ACT_NTI_ADMIN)
class SOLRIndexObjectView(AbstractAuthenticatedView):

	def _notify(self, context):
		context = removeAllProxies(context)
		notify(IndexObjectEvent(context))

	def __call__(self):
		request = self.request
		uid = request.subpath[0] if request.subpath else None
		if uid is None:
			raise hexc.HTTPUnprocessableEntity("Must specify an object id")
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
			raise hexc.HTTPUnprocessableEntity("Must specify an object id")
		context = object_finder(uid)
		if context is None:
			raise hexc.HTTPNotFound()
		self._notify(context)
		return hexc.HTTPNoContent()

@view_config(context=IUser)
@view_config(context=INTIMedia)
@view_config(context=IContentUnit)
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
@view_config(context=IContentUnit)
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

@view_config(name='IndexAllLibraries')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=SOLRPathAdapter,
			   permission=nauth.ACT_NTI_ADMIN)
class IndexAllLibrariesView(SOLRIndexObjectView):

	def __call__(self):
		library = component.queryUtility(IContentPackageLibrary)
		if library is not None:
			for package in library.contentPackages or ():
				if not IGlobalContentPackage.providedBy(package):
					self._notify(package)
		return hexc.HTTPNoContent()

@view_config(name='EmptyQueues')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=SOLRPathAdapter,
			   permission=nauth.ACT_NTI_ADMIN)
class EmptyQueuesView(SOLRIndexObjectView):

	def __call__(self):
		for name in QUEUE_NAMES:
			queue = get_job_queue(name)
			queue.empty()
		return hexc.HTTPNoContent()
