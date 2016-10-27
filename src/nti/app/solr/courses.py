#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.component.hooks import site as current_site

from nti.app.assessment.interfaces import IUsersCourseAssignmentHistories

from nti.contenttypes.courses.interfaces import ICourseInstance

from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.solr.common import finder
from nti.solr.common import get_job_site
from nti.solr.common import process_asset

from nti.solr.interfaces import ICoreCatalog

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

def process_course_assignment_feedback(obj, index=True):
	container = IUsersCourseAssignmentHistories(obj, None)
	if container is not None:
		for history in list(container.values()):
			for item in list(history.values()):
				for feedback in item.Feedback.Items:
					catalog = ICoreCatalog(feedback)
					operation = catalog.add if index else catalog.remove
					operation(obj, commit=False) # wait for server to commit

def index_course_assignment_feedback(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_assignment_feedback(obj, index=True)

def unindex_course_assignment_feedback(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_assignment_feedback(obj, index=False)
