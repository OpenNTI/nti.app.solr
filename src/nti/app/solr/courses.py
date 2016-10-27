#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.component.hooks import site as current_site

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.solr.common import finder
from nti.solr.common import get_job_site
from nti.solr.common import process_asset

def process_course_assets(obj, index=True):
	container = IPresentationAssetContainer(obj, None)
	if container:
		size = len(container) - 1
		for x, a in enumerate(container.values()):
			process_asset(a, index=index, commit=size == x)

def index_course_assets(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_assets(obj, index=True)

def unindex_course_assets(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_assets(obj, index=False)
