#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 3

from zope import component
from zope import interface

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from zope.event import notify

from nti.contenttypes.presentation import INTIVideo

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import get_all_host_sites

from nti.solr.interfaces import ICoreCatalog
from nti.solr.interfaces import IndexObjectEvent


@interface.implementer(IDataserver)
class MockDataserver(object):

    root = None

    def get_by_oid(self, oid, ignore_creator=False):
        resolver = component.queryUtility(IOIDResolver)
        if resolver is None:
            logger.warn("Using dataserver without a proper ISiteManager.")
        else:
            return resolver.get_object_by_oid(oid, ignore_creator=ignore_creator)
        return None


def _reindex_transcripts(seen):
    for name, video in list(component.getUtilitiesFor(INTIVideo)):
        if name in seen:
            continue
        seen.add(name)
        for transcript in video.transcripts or ():
            notify(IndexObjectEvent(transcript))


def do_evolve(context, generation=generation):
    logger.info("SOLR evolution %s started", generation)

    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert  component.getSiteManager() == ds_folder.getSiteManager(), \
                "Hooks not installed?"

        seen = set()
        # clear all transcripts
        catalog = component.getUtility(ICoreCatalog, name="transcripts")
        catalog.clear(commit=False)
        # re/index
        _reindex_transcripts(seen)
        for site in get_all_host_sites():
            with current_site(site):
                _reindex_transcripts(seen)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('SOLR Evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 3 by reindexing the transcripts
    """
    do_evolve(context)
