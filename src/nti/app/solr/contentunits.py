#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component.hooks import site as current_site

from nti.assessment.interfaces import IQAssessmentItemContainer

from nti.contentlibrary.interfaces import IContentPackage

from nti.solr import EVALUATIONS_QUEUE

from nti.solr.common import finder
from nti.solr.common import get_job_site
from nti.solr.common import add_to_queue

from nti.solr.interfaces import ICoreCatalog
from nti.solr.interfaces import IIndexObjectEvent
from nti.solr.interfaces import IUnindexObjectEvent


def process_content_package_evaluations(obj, index=True):
    collector = set()
    def recur(unit):
        container = IQAssessmentItemContainer(unit, None)
        if container:
            collector.update(container.values())
        for child in unit.children or ():
            recur(child)
    recur(obj)
    for a in collector:
        catalog = ICoreCatalog(a)
        operation = catalog.add if index else catalog.remove
        operation(a, commit=False)  # wait for server to commit


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
