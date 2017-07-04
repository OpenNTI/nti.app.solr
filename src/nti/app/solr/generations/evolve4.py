#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 4

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


def renderable_mimeTypes():
    try:
        from nti.contentlibrary import RENDERABLE_CONTENT_MIME_TYPES
        return RENDERABLE_CONTENT_MIME_TYPES
    except ImportError:
        return ()


def _reindex_units(seen, intids):
    try:
        from nti.contentlibrary.interfaces import IContentPackageLibrary
        from nti.contentlibrary.interfaces import IRenderableContentPackage
        library = component.queryUtility(IContentPackageLibrary)
        if library is None:
            return
        for package in library.contentPackages or ():
            if not IRenderableContentPackage.providedBy(package):
                continue
            doc_id = intids.queryId(package)
            if doc_id is None or doc_id in seen:
                continue
            seen.add(doc_id)
            notify(IndexObjectEvent(package))
    except ImportError:
        pass


def do_evolve(context, generation=generation):
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

        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)

        seen = set()
        # clear all renderable content units
        catalog = component.queryUtility(ICoreCatalog, name="contentunits")
        mimeTypes = renderable_mimeTypes()
        if catalog is not None and mimeTypes:
            catalog.clear(commit=False, mimeTypes=mimeTypes)
            for site in get_all_host_sites():
                with current_site(site):
                    _reindex_units(seen, intids)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('SOLR Evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 4 by reindexing the content renderable content units
    """
    do_evolve(context)
