#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.solr.views import SOLRPathAdapter

from nti.app.solr.views.general_views import SOLRIndexObjectView

from nti.contenttypes.courses.interfaces import ICourseCatalog
from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.contenttypes.courses.legacy_catalog import ILegacyCourseCatalogEntry

from nti.contenttypes.courses.utils import get_course_subinstances

from nti.dataserver import authorization as nauth

logger = __import__('logging').getLogger(__name__)


@view_config(context=ICourseInstance)
@view_config(context=ICourseCatalogEntry)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_index',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class IndexCourseView(SOLRIndexObjectView):

    def __call__(self):
        self._notify(ICourseInstance(self.context))
        for course in get_course_subinstances(self.context):
            self._notify(course)
        return hexc.HTTPNoContent()


@view_config(name='IndexAllCourses')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class IndexAllCoursesView(SOLRIndexObjectView):

    def predicate(self, context):
        return not ILegacyCourseCatalogEntry.providedBy(context)

    def __call__(self):
        catalog = component.queryUtility(ICourseCatalog)
        if catalog is not None:
            for entry in catalog.iterCatalogEntries():
                if self.predicate(entry):
                    course = ICourseInstance(entry)
                    self._notify(course)
        return hexc.HTTPNoContent()


@view_config(name='IndexLegacyCourses')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class IndexLegacyCoursesView(IndexAllCoursesView):

    def predicate(self, context):
        return ILegacyCourseCatalogEntry.providedBy(context)
