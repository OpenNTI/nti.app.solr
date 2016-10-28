#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope.component.hooks import site as current_site

from nti.app.assessment.interfaces import ICourseEvaluations
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
		for a in list(container.values()):
			process_asset(a, index=index, commit=False) # wait for server to commit

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
					operation(obj, commit=False)  # wait for server to commit

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

def process_course_evaluations(obj, index=True):
	container = ICourseEvaluations(obj, None)
	if container is not None:
		size = len(container) - 1
		for x, item in enumerate(list(container.values())):
			catalog = ICoreCatalog(item)
			operation = catalog.add if index else catalog.remove
			operation(obj, commit=size == x)

def index_course_evaluations(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_assignment_feedback(obj, index=True)

def unindex_course_evaluations(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_evaluations(obj, index=False)

def process_course_discussions(obj, index=True):
	board = obj.Discussions
	for forum in list(board.values()):
		catalog = ICoreCatalog(forum)
		operation = catalog.add if index else catalog.remove
		operation(obj, commit=False)
		for topic in list(forum.values()):
			catalog = ICoreCatalog(forum)
			operation = catalog.add if index else catalog.remove
			operation(obj, commit=False)
			for comment in list(topic.values()):
				catalog = ICoreCatalog(comment)
				operation = catalog.add if index else catalog.remove
				operation(comment, commit=False)  # wait for server to commit

def index_course_discussions(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_discussions(obj, index=True)

def unindex_course_discussions(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = ICourseInstance(finder(source), None)
		if ICourseInstance.providedBy(obj):
			process_course_discussions(obj, index=False)
