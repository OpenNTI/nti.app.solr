#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 2

from zope import component
from zope import interface

from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from zope.event import notify

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

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


def _reindex_legacy_content():
    try:
        from nti.contentlibrary.interfaces import IGlobalContentPackage
        from nti.contentlibrary.interfaces import IContentPackageLibrary
        library = component.queryUtility(IContentPackageLibrary)
        if library is None:
            return
        else:
            library.syncContentPackages()
            for package in library.contentPackages or ():
                if IGlobalContentPackage.providedBy(package):
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
        assert  component.getSiteManager() == ds_folder.getSiteManager(), \
                "Hooks not installed?"

        _reindex_legacy_content()

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('SOLR Evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 2 by reindexing legacy packages
    """
    do_evolve(context)
