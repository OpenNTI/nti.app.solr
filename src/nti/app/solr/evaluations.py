#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
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
	container = IQAssessmentItemContainer(obj, None)
	if container:
		size = len(container) - 1
		for x, a in enumerate(container.values()):
			catalog = ICoreCatalog(a)
			operation = catalog.add if index else catalog.remove
			operation(obj, commit=size == x)

def index_content_package_evaluations(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = finder(source)
		if IContentPackage.providedBy(obj):
			process_content_package_evaluations(obj, index=True)

def unindex_content_package_evaluations(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = finder(source)
		if IContentPackage.providedBy(obj):
			process_content_package_evaluations(obj, index=False)

@component.adapter(IContentPackage, IIndexObjectEvent)
def _index_contentpackage(obj, event):
	add_to_queue(EVALUATIONS_QUEUE, 
				 index_content_package_evaluations, obj, jid='evaluations_added')

@component.adapter(IContentPackage, IUnindexObjectEvent)
def _unindex_contentpackage(obj, event):
	add_to_queue(EVALUATIONS_QUEUE, unindex_content_package_evaluations, obj,
				 jid='evaluations_removed')
