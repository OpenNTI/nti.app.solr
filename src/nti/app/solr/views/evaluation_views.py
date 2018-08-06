#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from zope import component

from nti.app.solr.views import SOLRPathAdapter

from nti.app.solr.views.general_views import SOLRIndexObjectView
from nti.app.solr.views.general_views import UnindexSOLRObjectView

from nti.assessment.interfaces import IQEvaluation

from nti.dataserver import authorization as nauth

logger = __import__('logging').getLogger(__name__)


@view_config(context=IQEvaluation)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_index',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class IndexEvaluationView(SOLRIndexObjectView):

    def __call__(self):
        self._notify(self.context)
        return hexc.HTTPNoContent()


@view_config(context=IQEvaluation)
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               name='solr_unindex',
               request_method='POST',
               permission=nauth.ACT_NTI_ADMIN)
class UnindexEvaluationView(UnindexSOLRObjectView):

    def __call__(self):
        self._notify(self.context)
        return hexc.HTTPNoContent()


@view_config(name='IndexAllEvaluations')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class IndexAllEvaluationsView(SOLRIndexObjectView):

    def __call__(self):
        for _, obj in component.getUtilitiesFor(IQEvaluation):
            self._notify(obj)
        return hexc.HTTPNoContent()


@view_config(name='UnindexAllEvaluations')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class UnindexAllEvaluationsView(UnindexSOLRObjectView):

    def __call__(self):
        for _, obj in component.getUtilitiesFor(IQEvaluation):
            self._notify(obj)
        return hexc.HTTPNoContent()
