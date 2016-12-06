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

from nti.app.base.abstract_views import AbstractAuthenticatedView

from nti.app.solr.views import SOLRPathAdapter

from nti.dataserver import authorization as nauth

from nti.externalization.interfaces import LocatedExternalDict
from nti.externalization.interfaces import StandardExternalFields

from nti.solr import QUEUE_NAMES

from nti.solr.common import get_job_queue

ITEMS = StandardExternalFields.ITEMS
TOTAL = StandardExternalFields.TOTAL
ITEM_COUNT = StandardExternalFields.ITEM_COUNT

@view_config(name='Jobs')
@view_config(name='jobs')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='GET',
			   context=SOLRPathAdapter,
			   permission=nauth.ACT_NTI_ADMIN)
class QueueJobsView(AbstractAuthenticatedView):

	def __call__(self):
		total = 0
		result = LocatedExternalDict()
		items = result[ITEMS] = {}
		for name in QUEUE_NAMES:
			queue = get_job_queue(name)
			items[name] = list(queue.keys())  # snapshopt
			total += len(items[name])
		result[TOTAL] = result[ITEM_COUNT] = total
		return result

@view_config(name='EmptyQueues')
@view_config(name='empty_queues')
@view_defaults(route_name='objects.generic.traversal',
			   renderer='rest',
			   request_method='POST',
			   context=SOLRPathAdapter,
			   permission=nauth.ACT_NTI_ADMIN)
class EmptyQueuesView(AbstractAuthenticatedView):

	def __call__(self):
		for name in QUEUE_NAMES:
			queue = get_job_queue(name)
			queue.empty()
		return hexc.HTTPNoContent()
