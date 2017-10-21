#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.component.hooks import site as current_site

from nti.contenttypes.courses.interfaces import ICourseInstance
from nti.contenttypes.courses.interfaces import ICourseSubInstance
from nti.contenttypes.courses.interfaces import ICourseCatalogEntry
from nti.contenttypes.courses.interfaces import ICourseInstanceImportedEvent

from nti.contenttypes.courses.utils import get_course_hierarchy

from nti.contenttypes.presentation.interfaces import IConcreteAsset
from nti.contenttypes.presentation.interfaces import IUserCreatedAsset
from nti.contenttypes.presentation.interfaces import IPresentationAssetContainer

from nti.solr import COURSES_QUEUE

from nti.solr.common import finder
from nti.solr.common import add_to_queue
from nti.solr.common import get_job_site
from nti.solr.common import process_asset

from nti.solr.interfaces import ICoreCatalog
from nti.solr.interfaces import IIndexObjectEvent

logger = __import__('logging').getLogger(__name__)


def process_course_assets(obj, index=True):
    container = IPresentationAssetContainer(obj, None)
    if container:
        for a in list(container.values()):
            a = IConcreteAsset(a, a)
            if IUserCreatedAsset.providedBy(a):
                # wait for server to commit
                process_asset(a, index=index, commit=False)


def index_course_assets(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = ICourseInstance(finder(source), None)
        if ICourseInstance.providedBy(obj):
            entry = ICourseCatalogEntry(obj, None)
            ntiid = getattr(entry, 'ntiid', None) or obj
            logger.info("Course %s assets indexing started", ntiid)
            process_course_assets(obj, index=True)
            logger.info("Course %s assets indexing completed", ntiid)


def unindex_course_assets(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = ICourseInstance(finder(source), None)
        if ICourseInstance.providedBy(obj):
            process_course_assets(obj, index=False)


def process_course_assignment_feedback(obj, index=True):
    try:
        from nti.app.assessment.interfaces import IUsersCourseAssignmentHistories
        container = IUsersCourseAssignmentHistories(obj, None)
        if container is not None:
            for history in list(container.values()):
                for item in list(history.values()):
                    for feedback in item.Feedback.Items:
                        catalog = ICoreCatalog(feedback)
                        operation = catalog.add if index else catalog.remove
                        # wait for server to commit
                        operation(feedback, commit=False)
    except ImportError:
        pass


def index_course_assignment_feedback(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = ICourseInstance(finder(source), None)
        if ICourseInstance.providedBy(obj):
            entry = ICourseCatalogEntry(obj, None)
            ntiid = getattr(entry, 'ntiid', None) or obj
            logger.info("Course %s assignment feedback indexing started", ntiid)
            process_course_assignment_feedback(obj, index=True)
            logger.info("Course %s assignment feedback indexing completed", ntiid)


def unindex_course_assignment_feedback(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = ICourseInstance(finder(source), None)
        if ICourseInstance.providedBy(obj):
            process_course_assignment_feedback(obj, index=False)


def process_course_evaluations(obj, index=True):
    try:
        from nti.app.assessment.interfaces import IQEvaluations
        container = IQEvaluations(obj, None)
        if container is not None:
            for item in list(container.values()):
                catalog = ICoreCatalog(item)
                operation = catalog.add if index else catalog.remove
                operation(item, commit=False)  # wait for server to commit
    except ImportError:
        pass


def index_course_evaluations(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = ICourseInstance(finder(source), None)
        if ICourseInstance.providedBy(obj):
            entry = ICourseCatalogEntry(obj, None)
            ntiid = getattr(entry, 'ntiid', None) or obj
            logger.info("Course %s evaluations indexing started", ntiid)
            process_course_evaluations(obj, index=True)
            logger.info("Course %s evaluations indexing completed", ntiid)


def unindex_course_evaluations(source, site=None, *unused_args, **unused_kwargs):
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
        operation(forum, commit=False)
        for topic in list(forum.values()):
            catalog = ICoreCatalog(topic.headline)
            operation = catalog.add if index else catalog.remove
            operation(topic.headline, commit=False) # posts
            for comment in list(topic.values()):
                catalog = ICoreCatalog(comment)
                operation = catalog.add if index else catalog.remove
                operation(comment, commit=False)  # wait for server to commit


def index_course_discussions(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = ICourseInstance(finder(source), None)
        if ICourseInstance.providedBy(obj):
            entry = ICourseCatalogEntry(obj, None)
            ntiid = getattr(entry, 'ntiid', None) or obj
            logger.info("Course %s discussions indexing started", ntiid)
            process_course_discussions(obj, index=True)
            logger.info("Course %s discussions indexing started", ntiid)


def unindex_course_discussions(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = ICourseInstance(finder(source), None)
        if ICourseInstance.providedBy(obj):
            process_course_discussions(obj, index=False)


@component.adapter(ICourseInstance, IIndexObjectEvent)
def _index_course(obj, _):
    add_to_queue(COURSES_QUEUE,
                 index_course_assets,
                 obj, 
                 jid='assets_added')

    add_to_queue(COURSES_QUEUE, 
                 index_course_evaluations, 
                 obj, 
                 jid='evaluations_added')

    add_to_queue(COURSES_QUEUE,
                 index_course_discussions, 
                 obj, 
                 jid='discussions_added')

    add_to_queue(COURSES_QUEUE, 
                 index_course_assignment_feedback, 
                 obj, 
                 jid='feedback_added')


@component.adapter(ICourseInstance, ICourseInstanceImportedEvent)
def _course_imported(obj, _):
    if not ICourseSubInstance.providedBy(obj):
        for course in get_course_hierarchy(obj):
            _index_course(course, None)
