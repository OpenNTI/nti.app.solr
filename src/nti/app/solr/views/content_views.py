#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.solr.views import SOLRPathAdapter

from nti.app.solr.views.general_views import SOLRIndexObjectView
from nti.app.solr.views.general_views import UnindexSOLRObjectView

from nti.contentlibrary.interfaces import IContentUnit
from nti.contentlibrary.interfaces import IGlobalContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver import authorization as nauth


@view_config(context=IContentUnit)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_index',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class IndexObjectView(SOLRIndexObjectView):

    def __call__(self):
        self._notify(self.context)
        return hexc.HTTPNoContent()


@view_config(context=IContentUnit)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_unindex',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class UnindexObjectView(UnindexSOLRObjectView):

    def __call__(self):
        self._notify(self.context)
        return hexc.HTTPNoContent()


@view_config(name='IndexAllContentPackages')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class IndexAllContentPackagesView(SOLRIndexObjectView):

    def predicate(self, context):
        return not IGlobalContentPackage.providedBy(context)

    def __call__(self):
        library = component.queryUtility(IContentPackageLibrary)
        if library is not None:
            for package in library.contentPackages or ():
                if self.predicate(package):
                    self._notify(package)
        return hexc.HTTPNoContent()


@view_config(name='IndexLegacyContentPackages')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class IndexLegacyContentPackagesView(IndexAllContentPackagesView):

    def predicate(self, context):
        return IGlobalContentPackage.providedBy(context)
