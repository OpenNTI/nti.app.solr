#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

import os
import sys
import time
import logging
import argparse
import itertools
import transaction

import zope.exceptions

from zope import component

from zope.component.hooks import site as current_site

from zope.container.contained import Contained

from zope.event import notify

from zope.intid.interfaces import IIntIds

from nti.appserver.policies.interfaces import ISitePolicyUserEventListener

from nti.contentlibrary.interfaces import IGlobalContentPackage
from nti.contentlibrary.interfaces import IContentPackageLibrary

from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.dataserver.users.communities import Community

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import create_context

from nti.site.hostpolicy import get_all_host_sites

from nti.site.site import get_site_for_site_names

from nti.solr.interfaces import IndexObjectEvent

#: How often to log progress and savepoints.
LOG_ITER_COUNT = 1000
#: How often we commit work
DEFAULT_COMMIT_BATCH_SIZE = 2000

class PluginPoint(Contained):

	def __init__(self, name):
		self.__name__ = name

PP_APP = PluginPoint('nti.app')
PP_APP_SITES = PluginPoint('nti.app.sites')
PP_APP_PRODUCTS = PluginPoint('nti.app.products')

class _SolrInitializer(object):

	def __init__(self, batch_size, site_name, seen_intids, seen_ntiids):
		self.batch_size = batch_size
		self.seen_intids = seen_intids
		self.seen_ntiids = seen_ntiids
		self.site_name = site_name

	def process_obj(self, obj, intids):
		logger.info( '[%s] Processing (%s) (%s) (%s)',
					  self.site_name, obj,
					  intids.queryId( obj ),
					  getattr( obj, 'ntiid', None ) )
		notify( IndexObjectEvent( obj ) )

	def _is_new_object(self, obj, intids):
		"""
		Defines if the given object has been processed yet.
		"""
		obj_id = intids.queryId( obj )
		obj_ntiid = getattr( obj, 'ntiid', None )

		if 		(obj_id is not None and obj_id in self.seen_intids) \
			or 	(obj_ntiid is not None and obj_ntiid in self.seen_ntiids):
			return False

		if obj_id is not None:
			self.seen_intids.add( obj_id )
		if obj_ntiid is not None:
			self.seen_ntiids.add( obj_ntiid )
		if obj_ntiid is None and obj_id is None:
			logger.warn( 'Object without ntiid or intid (%s)', obj )
			return False
		return True

	def user_iter(self):
		site_policy = component.queryUtility( ISitePolicyUserEventListener )
		community_username = getattr(site_policy, 'COM_USERNAME', '')
		if community_username:
			site_community = Community.get_community( community_username )
			if site_community is not None:
				logger.warn( "[%s] Using community %s", self.site_name, community_username )
				try:
					return site_community.iter_members()
				except AttributeError:
					logger.warn( "[%s] Not an iterable community (%s)",
								 self.site_name, community_username )
		logger.warn( "[%s] No community found for site", self.site_name )

	def package_iter(self):
		catalog = component.queryUtility( IContentPackageLibrary )
		if catalog is not None:
			for package in catalog.contentPackages or ():
				if not IGlobalContentPackage.providedBy( package ):
					yield package

	def course_iter(self):
		try:
			from nti.contenttypes.courses.interfaces import ICourseCatalog
			from nti.contenttypes.courses.interfaces import ICourseInstance
			catalog = component.getUtility( ICourseCatalog )
			for entry in catalog.iterCatalogEntries():
				course = ICourseInstance( entry, None )
				if course is not None:
					yield course
		except (ImportError, component.ComponentLookupError):
			return

	def init_solr(self):
		our_site = get_site_for_site_names( (self.site_name,) )
		with current_site( our_site ):
			count = 0
			intids = component.getUtility(IIntIds)
			for obj in itertools.chain( self.course_iter() or (),
										self.package_iter() or (),
										self.user_iter() or ()):
				if self._is_new_object(obj, intids):
					self.process_obj(obj, intids)
					count += 1
					if count % LOG_ITER_COUNT == 0:
						logger.info('[%s] Processed %s objects...',
									self.site_name, count)
						transaction.savepoint(optimistic=True)
				if self.batch_size and count > self.batch_size:
					break
			return count

	def __call__(self):
		logger.info('[%s] Initializing solr intializer (batch_size=%s)',
					self.site_name, self.batch_size)
		now = time.time()
		total = 0

		transaction_runner = component.getUtility(IDataserverTransactionRunner)

		while True:
			try:
				count = transaction_runner(self.init_solr, retries=2, sleep=1)
				total += count
				logger.info('[%s] Committed batch (%s) (total=%s)',
							 self.site_name, count, total)

				if 		(self.batch_size and count <= self.batch_size) \
					or 	self.batch_size is None:
					break
			except KeyboardInterrupt:
				logger.info('[%s] Exiting solr initializer', self.site_name)
				break

		elapsed = time.time() - now
		logger.info("[%s] Total objects processed (size=%s) (time=%s)",
					self.site_name, total, elapsed)

class Processor(object):

	def create_arg_parser(self):
		arg_parser = argparse.ArgumentParser(description="Create a user-type object")
		arg_parser.add_argument('--env_dir', dest='env_dir',
								help="Dataserver environment root directory")
		arg_parser.add_argument('--batch_size', dest='batch_size',
								help="Commit after each batch")
		arg_parser.add_argument('--site', dest='site', help="request SITE")
		arg_parser.add_argument('-v', '--verbose', help="Be verbose",
								action='store_true', dest='verbose')
		return arg_parser

	def set_log_formatter(self, args):
		ei = '%(asctime)s %(levelname)-5.5s [%(name)s][%(thread)d][%(threadName)s] %(message)s'
		logging.root.handlers[0].setFormatter(zope.exceptions.log.Formatter(ei))

	def process_args(self, args):
		self.set_log_formatter(args)
		site_name = getattr(args, 'site', None)
		sites = None
		if site_name:
			site = get_site_for_site_names( tuple( site_name ) )
			sites = (site,)

		batch_size = DEFAULT_COMMIT_BATCH_SIZE
		if args.batch_size:
			batch_size = args.batch_size

		seen_intids = set()
		seen_ntiids = set()
		ds = component.getUtility(IDataserver)
		with current_site(ds.dataserver_folder):
			sites = get_all_host_sites() if sites is None else sites
			for site in sites:
				solr_initializer = _SolrInitializer(batch_size, site.__name__,
													seen_intids, seen_ntiids)
				solr_initializer()
		sys.exit()

	def __call__(self, *args, **kwargs):
		arg_parser = self.create_arg_parser()
		args = arg_parser.parse_args()

		env_dir = args.env_dir
		if not env_dir:
			env_dir = os.getenv('DATASERVER_DIR')
		if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
			raise ValueError("Invalid dataserver environment root directory", env_dir)

		conf_packages = ('nti.solr', 'nti.appserver', 'nti.dataserver',)
		context = create_context(env_dir, with_library=True)

		run_with_dataserver(environment_dir=env_dir,
							xmlconfig_packages=conf_packages,
							verbose=args.verbose,
							context=context,
							use_transaction_runner=True,
							function=lambda: self.process_args(args))

def main():
	return Processor()()

if __name__ == '__main__':
	main()
