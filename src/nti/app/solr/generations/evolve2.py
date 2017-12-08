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

from zope.component.hooks import getSite
from zope.component.hooks import setHooks
from zope.component.hooks import site as current_site

from zope.event import notify

from nti.contenttypes.courses.utils import get_courses_for_packages

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IOIDResolver

from nti.site.hostpolicy import get_all_host_sites

from nti.solr.interfaces import IndexObjectEvent

generation = 2

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


def _sync_library():
    try:
        from nti.contentlibrary.interfaces import IContentPackageLibrary
        library = component.queryUtility(IContentPackageLibrary)
        if library is not None:
            library.syncContentPackages()
    except ImportError:  # pragma: no cover
        pass


def _reindex_legacy_content(seen):
    try:
        sites = getSite().__name__ or ''
        from nti.contentlibrary.interfaces import IGlobalContentPackage
        from nti.contentlibrary.interfaces import IContentPackageLibrary
        library = component.queryUtility(IContentPackageLibrary)
        if library is not None:
            for context in library.contentPackages or ():
                ntiid = context.ntiid
                if ntiid in seen:
                    continue
                seen.add(ntiid)
                # global content
                if IGlobalContentPackage.providedBy(context):
                    notify(IndexObjectEvent(context))
                else:  # package w/o course references
                    courses = get_courses_for_packages(sites=sites,
                                                       packages=(ntiid,))
                    if not courses:
                        notify(IndexObjectEvent(context))
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

        # global site
        seen = set()
        _sync_library()
        _reindex_legacy_content(seen)
        for site in get_all_host_sites():
            with current_site(site):
                _reindex_legacy_content(seen)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('SOLR Evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 2 by reindexing legacy packages
    """
    do_evolve(context)
