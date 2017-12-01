#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=W0212,W0621,W0703

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

generation = 6

logger = __import__('logging').getLogger(__name__)

try:
    from nti.contenttypes.courses.interfaces import ICourseCatalog
except ImportError:
    HAS_COURSES = False
else:
    HAS_COURSES = True


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
    except ImportError:
        pass


def _process_site(seen, intids):
    from nti.contenttypes.courses.interfaces import ICourseInstance
    catalog = component.queryUtility(ICourseCatalog)
    if catalog is None or catalog.isEmpty():
        return
    for entry in catalog.iterCatalogEntries():
        course = ICourseInstance(entry)
        doc_id = intids.queryId(course)
        if doc_id is None or doc_id in seen:
            continue
        seen.add(doc_id)
        notify(IndexObjectEvent(course))


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

        seen = set()
        lsm = ds_folder.getSiteManager()
        intids = lsm.getUtility(IIntIds)
        # sync library
        if HAS_COURSES:
            _sync_library()
        # clear all courses
        catalog = component.queryUtility(ICoreCatalog, name="courses")
        if catalog is not None and HAS_COURSES:
            catalog.clear(commit=False)
            for site in get_all_host_sites():
                with current_site(site):
                    _process_site(seen, intids)

    component.getGlobalSiteManager().unregisterUtility(mock_ds, IDataserver)
    logger.info('SOLR Evolution %s done', generation)


def evolve(context):
    """
    Evolve to generation 6 by reindexing the course objects
    """
    do_evolve(context)
