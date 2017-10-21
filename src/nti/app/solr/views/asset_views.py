#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from pyramid import httpexceptions as hexc

from pyramid.view import view_config
from pyramid.view import view_defaults

from nti.app.solr.views import SOLRPathAdapter

from nti.app.solr.views.general_views import SOLRIndexObjectView
from nti.app.solr.views.general_views import UnindexSOLRObjectView

from nti.contenttypes.presentation.interfaces import INTIMedia

from nti.dataserver import authorization as nauth

logger = __import__('logging').getLogger(__name__)


def all_transcripts():
    for _, obj in component.getUtilitiesFor(INTIMedia):
        for transcript in getattr(obj, 'transcripts', None) or ():
            yield transcript


@view_config(name='IndexAllTranscripts')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class IndexAllTranscriptsView(SOLRIndexObjectView):

    def __call__(self):
        for transcript in all_transcripts():
            self._notify(transcript)
        return hexc.HTTPNoContent()


@view_config(name='UnindexAllTranscripts')
@view_defaults(route_name='objects.generic.traversal',
               renderer='rest',
               request_method='POST',
               context=SOLRPathAdapter,
               permission=nauth.ACT_NTI_ADMIN)
class UnindexAllTranscriptsView(UnindexSOLRObjectView):

    def __call__(self):
        for transcript in all_transcripts():
            self._notify(transcript)
        return hexc.HTTPNoContent()
