#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component
from zope import interface

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from zope.event import notify

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import get_all_host_sites

from nti.solr.interfaces import ICoreCatalog
from nti.solr.interfaces import IndexObjectEvent

generation = 8

logger = __import__('logging').getLogger(__name__)


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


def _survey_mimeTypes():
    try:
        from nti.assessment.interfaces import SURVEY_MIME_TYPE
        return (SURVEY_MIME_TYPE,)
    except ImportError:  # pragma: no cover
        return ()


def _process_site(seen, intids):
    try:
        from nti.assessment.interfaces import IQSurvey
        for _, item in component.getUtilitiesFor(IQSurvey):
            doc_id = intids.queryId(item)
            if doc_id is None or doc_id in seen:
                continue
            seen.add(doc_id)
            if item.isPublished():
                notify(IndexObjectEvent(item))
    except ImportError:  # pragma: no cover
        pass


def do_evolve(context, generation=generation):  # pylint: disable=redefined-outer-name
    logger.info("SOLR evolution %s started", generation)

    setHooks()
    conn = context.connection
    ds_folder = conn.root()['nti.dataserver']

    mock_ds = MockDataserver()
    mock_ds.root = ds_folder
    component.provideUtility(mock_ds, IDataserver)

    with current_site(ds_folder):
        assert component.getSiteManager() == ds_folder.getSiteManager(), \
               "Hooks not installed?"

        seen = set()
        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        # clear all surveys
        mimeTypes = _survey_mimeTypes()

        catalog = component.queryUtility(ICoreCatalog, name="evaluations")
        if catalog is not None and mimeTypes:
            catalog.clear(commit=False, mimeTypes=mimeTypes)
            for site in get_all_host_sites():
                with current_site(site):
                    _process_site(seen, intids)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('SOLR Evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 8 by reindexing the survey objects
    """
    do_evolve(context)
