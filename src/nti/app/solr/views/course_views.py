#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.solr.views.general_views import SOLRIndexObjectView

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry

from nti.contenttypes.courses.utils import get_course_subinstances

from nti.dataserver import authorization as nauth

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
