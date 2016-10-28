#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import component

from zope.component.hooks import site as current_site

from zope.intid.interfaces import IIntIds

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IUserGeneratedData

from nti.dataserver.metadata_index import IX_CREATOR
from nti.dataserver.metadata_index import IX_SHAREDWITH

from nti.metadata import dataserver_metadata_catalog

from nti.solr.common import finder
from nti.solr.common import get_job_site

from nti.solr.interfaces import ICoreCatalog

def all_user_generated_data(users=(), sharedWith=False):
	intids = component.getUtility(IIntIds)
	catalog = dataserver_metadata_catalog()
	usernames = {getattr(user, 'username', user).lower() for user in users or ()}
	if usernames:
		uids = catalog[IX_CREATOR].apply({'any_of': usernames})
	else:
		uids = catalog[IX_CREATOR].ids()

	for uid in uids or ():
		obj = intids.queryObject(uid)
		if IUserGeneratedData.providedBy(obj):
			yield uid, obj

	if usernames and sharedWith:
		intids_sharedWith = catalog[IX_SHAREDWITH].apply({'any_of': usernames})
		for uid in intids_sharedWith or ():
			obj = intids.queryObject(uid)
			if IUserGeneratedData.providedBy(obj):
				yield uid, obj
			
def process_userdata(user, index=True):
	for _, obj in all_user_generated_data(users=(user,)):
		catalog = ICoreCatalog(obj)
		operation = catalog.add if index else catalog.remove
		operation(obj, commit=False)  # wait for server to commit

def index_userdata(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = IUser(finder(source), None)
		if IUser.providedBy(obj):
			logger.info("Indexing data for user %s started", obj)
			process_userdata(obj, index=True)
			logger.info("Indexing data for user %s completed", obj)

def unindex_userdata(source, site=None, *args, **kwargs):
	job_site = get_job_site(site)
	with current_site(job_site):
		obj = IUser(finder(source), None)
		if IUser.providedBy(obj):
			process_userdata(obj, index=False)
