#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import component

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserGeneratedData

from nti.dataserver.metadata.index import IX_TOPICS
from nti.dataserver.metadata.index import IX_CREATOR
from nti.dataserver.metadata.index import IX_SHAREDWITH
from nti.dataserver.metadata.index import TP_USER_GENERATED_DATA

from nti.dataserver.metadata.index import get_metadata_catalog

from nti.solr.common import finder
from nti.solr.common import add_to_queue

from nti.solr.interfaces import ICoreCatalog
from nti.solr.interfaces import IIndexObjectEvent

from nti.solr.userdata import USERDATA_QUEUE

logger = __import__('logging').getLogger(__name__)


def all_user_generated_data(users=(), sharedWith=False):
    seen = set()
    catalog = get_metadata_catalog()
    intids = component.getUtility(IIntIds)

    # get user data objects
    usernames = {
        getattr(user, 'username', user).lower() for user in users or ()
    }
    if usernames:
        user_ids = catalog[IX_CREATOR].apply({'any_of': usernames})
    else:
        user_ids = intids.family.IF.LFSet(catalog[IX_CREATOR].ids())

    # filter with ugds
    ugd_ids = catalog[IX_TOPICS][TP_USER_GENERATED_DATA].getExtent()
    toplevel_intids = ugd_ids.intersection(user_ids) if user_ids else None
    
    for uid in toplevel_intids or ():
        obj = intids.queryObject(uid)
        if IUserGeneratedData.providedBy(obj) and uid not in seen:
            yield uid, obj
            seen.add(uid)

    if usernames and sharedWith:
        sw_ids = catalog[IX_SHAREDWITH].apply({'any_of': usernames})
        toplevel_intids = ugd_ids.intersection(sw_ids) if sw_ids else None
        for uid in toplevel_intids or ():
            obj = intids.queryObject(uid)
            if IUserGeneratedData.providedBy(obj) and uid not in seen:
                yield uid, obj
                seen.add(uid)


def process_userdata(user, index=True):
    for _, obj in all_user_generated_data(users=(user,)):
        catalog = ICoreCatalog(obj)
        operation = catalog.add if index else catalog.remove
        operation(obj, commit=False)  # wait for server to commit


def index_userdata(source, unused_site=None, *unused_args, **unused_kwargs):
    obj = IUser(finder(source), None)
    if IUser.providedBy(obj):
        logger.info("Indexing data for user %s started", obj)
        process_userdata(obj, index=True)
        logger.info("Indexing data for user %s completed", obj)


def unindex_userdata(source, unused_site=None, *unused_args, **unused_kwargs):
    obj = IUser(finder(source), None)
    if IUser.providedBy(obj):
        process_userdata(obj, index=False)


@component.adapter(IUser, IIndexObjectEvent)
def _index_user(obj, _):
    add_to_queue(USERDATA_QUEUE, index_userdata, obj=obj,
                 jid='userdata_indexing')
