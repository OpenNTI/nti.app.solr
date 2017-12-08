#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=unused-argument

from zope import component

from zope.component.hooks import site as current_site

from nti.assessment.interfaces import IQAssessmentItemContainer

from nti.contentlibrary.interfaces import IContentPackage
from nti.contentlibrary.interfaces import IEditableContentPackage

from nti.solr.assessment import EVALUATIONS_QUEUE

from nti.solr.common import finder
from nti.solr.common import get_job_site
from nti.solr.common import add_to_queue

from nti.solr.interfaces import ICoreCatalog
from nti.solr.interfaces import IIndexObjectEvent
from nti.solr.interfaces import IUnindexObjectEvent

logger = __import__('logging').getLogger(__name__)


def _package_authored_evaluations(obj):
    try:
        from nti.app.assessment.interfaces import IQEvaluations
        container = IQEvaluations(obj, None)
        return container.values() if container else ()
    except ImportError:  # pragma: no cover
        return ()


def _package_native_evaluations(obj):
    collector = list()
    def recur(unit):
        container = IQAssessmentItemContainer(unit, None)
        if container:
            collector.extend(container.values())
        for child in unit.children or ():
            recur(child)
    recur(obj)
    return collector


def process_content_package_evaluations(obj, index=True):
    if IEditableContentPackage.providedBy(obj):
        items = _package_authored_evaluations(obj)
    else:
        items = _package_native_evaluations(obj)
    for item in items:
        catalog = ICoreCatalog(item)
        operation = catalog.add if index else catalog.remove
        operation(item, commit=False)  # wait for server to commit


def index_content_package_evaluations(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = finder(source)
        if IContentPackage.providedBy(obj):
            ntiid = obj.ntiid
            logger.info("Content package %s evaluations indexing started", ntiid)
            process_content_package_evaluations(obj, index=True)
            logger.info("Content package %s evaluations indexing completed", ntiid)


def unindex_content_package_evaluations(source, site=None, *unused_args, **unused_kwargs):
    job_site = get_job_site(site)
    with current_site(job_site):
        obj = finder(source)
        if IContentPackage.providedBy(obj):
            process_content_package_evaluations(obj, index=False)


@component.adapter(IContentPackage, IIndexObjectEvent)
def _index_contentpackage(obj, _):
    add_to_queue(EVALUATIONS_QUEUE,
                 index_content_package_evaluations, obj, jid='evaluations_added')


@component.adapter(IContentPackage, IUnindexObjectEvent)
def _unindex_contentpackage(obj, _):
    add_to_queue(EVALUATIONS_QUEUE, unindex_content_package_evaluations, obj,
                 jid='evaluations_removed')
