#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import time
import logging
import argparse
import transaction
from functools import partial

from zope import component

from zope.component.hooks import getSite
from zope.component.hooks import site as current_site

from zope.event import notify

from zope.exceptions.log import Formatter as ExceptionFormatter

from zope.intid.interfaces import IIntIds

from nti.app.users.utils import get_community_or_site_members

from nti.dataserver.interfaces import IUser
from nti.dataserver.interfaces import IDataserver
from nti.dataserver.interfaces import IShardLayout
from nti.dataserver.interfaces import IDataserverTransactionRunner

from nti.dataserver.utils import run_with_dataserver

from nti.dataserver.utils.base_script import create_context

from nti.site.hostpolicy import get_host_site
from nti.site.hostpolicy import get_all_host_sites

from nti.solr.interfaces import IndexObjectEvent

#: How often to log progress and savepoints.
LOG_ITER_COUNT = 1000

#: How often we commit work
DEFAULT_COMMIT_BATCH_SIZE = 2000

logger = __import__('logging').getLogger(__name__)


class _SolrInitializer(object):

    def __init__(self, batch_size, site_name, seen_intids, seen_ntiids):
        self.site_name = site_name
        self.batch_size = batch_size
        self.seen_intids = seen_intids
        self.seen_ntiids = seen_ntiids

    def process_obj(self, obj, intids):
        logger.info('[%s] Processing (%s) (%s) (%s)',
                    self.site_name, obj,
                    intids.queryId(obj),
                    getattr(obj, 'ntiid', None))
        notify(IndexObjectEvent(obj))

    def _is_new_object(self, obj, intids):
        """
        Defines if the given object has been processed yet.
        """
        obj_id = intids.queryId(obj)
        obj_ntiid = getattr(obj, 'ntiid', None)

        if     (obj_id is not None and obj_id in self.seen_intids) \
            or (obj_ntiid is not None and obj_ntiid in self.seen_ntiids):
            return False

        if obj_id is not None:
            self.seen_intids.add(obj_id)
        if obj_ntiid:
            self.seen_ntiids.add(obj_ntiid)
        if not obj_ntiid and obj_id is None:
            logger.warning('Object without ntiid or intid (%s)', obj)
            return False
        return True

    def user_iter(self):
        for user in get_community_or_site_members(True):
            yield user

    def all_users_iter(self):
        dataserver = component.getUtility(IDataserver)
        users = IShardLayout(dataserver).users_folder
        for user in users.values():  # pylint: disable=no-member
            if IUser.providedBy(user):
                yield user

    def package_iter(self):
        try:
            from nti.contentlibrary.interfaces import IGlobalContentPackage
            from nti.contentlibrary.interfaces import IContentPackageLibrary
            catalog = component.queryUtility(IContentPackageLibrary)
            if catalog is not None:
                for package in catalog.contentPackages or ():
                    if not IGlobalContentPackage.providedBy(package):
                        yield package
        except (ImportError):
            return

    def course_iter(self):
        try:
            from nti.contenttypes.courses.interfaces import ICourseCatalog
            from nti.contenttypes.courses.interfaces import ICourseInstance
            catalog = component.getUtility(ICourseCatalog)
            for entry in catalog.iterCatalogEntries():
                course = ICourseInstance(entry, None)
                if course is not None:
                    yield course
        except (ImportError, component.ComponentLookupError):
            return

    def _init_iter(self, iterable, intids, count):
        for obj in iterable or ():
            if self._is_new_object(obj, intids):
                self.process_obj(obj, intids)
                count += 1
                if count % LOG_ITER_COUNT == 0:
                    logger.info('[%s] Processed %s objects...',
                                self.site_name, count)
                    transaction.savepoint(optimistic=True)
            if self.batch_size and count > self.batch_size:
                return (True, count)
        return (False, count)

    def init_solr(self, all_users=False, site_users=True, courses=True, packages=True):
        if self.site_name == getSite().__name__:  # global site
            our_site = getSite()
        else:
            our_site = get_host_site(self.site_name)
        with current_site(our_site):
            count = 0
            intids = component.getUtility(IIntIds)
            if courses:
                must_break, count = self._init_iter(self.course_iter(),
                                                    intids,
                                                    count)
                if must_break:
                    return count
            if packages:
                must_break, count = self._init_iter(self.package_iter(),
                                                    intids,
                                                    count)
                if must_break:
                    return count
            if site_users:
                must_break, count = self._init_iter(self.user_iter(),
                                                    intids,
                                                    count)
                if must_break:
                    return count
            elif all_users:
                must_break, count = self._init_iter(self.all_users_iter(),
                                                    intids,
                                                    count)
                if must_break:
                    return count
            return count

    def run(self, all_users=False, site_users=True, courses=True, packages=True):
        total = 0
        now = time.time()
        logger.info('[%s] Initializing solr intializer (batch_size=%s)',
                    self.site_name, self.batch_size)

        runner = partial(self.init_solr,
                         all_users=all_users,
                         site_users=site_users,
                         courses=courses,
                         packages=packages)
        transaction_runner = component.getUtility(IDataserverTransactionRunner)
        while True:
            try:
                count = transaction_runner(runner, retries=2, sleep=1)
                total += count
                logger.info('[%s] Committed batch (%s) (total=%s)',
                            self.site_name, count, total)

                if self.batch_size is None or count <= self.batch_size:
                    break
            except KeyboardInterrupt:
                logger.info('[%s] Exiting solr initializer', self.site_name)
                break

        elapsed = time.time() - now
        logger.info("[%s] Total objects processed (size=%s) (time=%s)",
                    self.site_name, total, elapsed)
    __call__ = run  # alias


class Processor(object):

    def create_arg_parser(self):
        arg_parser = argparse.ArgumentParser(description="SOLR Initializer")

        arg_parser.add_argument('-b', '--batch_size', dest='batch_size',
                                help="Commit after each batch")

        site_group = arg_parser.add_mutually_exclusive_group()
        site_group.add_argument('-s', '--site', help="request site",
                                dest='site')
        site_group.add_argument('--all-sites', dest='all_sites',
                                help="Index all sites", action='store_true')

        arg_parser.add_argument('-v', '--verbose', help="Be verbose",
                                action='store_true', dest='verbose')

        arg_parser.add_argument('-c', '--courses', help="Index courses",
                                action='store_true', dest='courses')

        arg_parser.add_argument('-p', '--packages', help="Index packages",
                                action='store_true', dest='packages')

        site_group = arg_parser.add_mutually_exclusive_group()
        site_group.add_argument('-u', '--users', help="Index site users",
                                action='store_true', dest='site_users')
        site_group.add_argument('--all-users', dest='all_users',
                                help="Index all users", action='store_true')
        return arg_parser

    def set_log_formatter(self, unused_args):
        ei = '%(asctime)s %(levelname)-5.5s [%(name)s][%(thread)d][%(threadName)s] %(message)s'
        logging.root.handlers[0].setFormatter(ExceptionFormatter(ei))

    def _load_library(self):
        try:
            from nti.contentlibrary.interfaces import IContentPackageLibrary
            library = component.queryUtility(IContentPackageLibrary)
            if library is not None:
                library.syncContentPackages()
        except ImportError:
            pass

    def process_args(self, args):
        self.set_log_formatter(args)
        site_name = getattr(args, 'site', None)
        if site_name:
            sites = (get_host_site(site_name),)
        elif getattr(args, 'all_sites', False):
            sites = get_all_host_sites()
        else:
            sites = (getSite(),)

        batch_size = DEFAULT_COMMIT_BATCH_SIZE
        if args.batch_size:
            batch_size = args.batch_size

        # load library before running transaction runner
        if args.packages or args.courses:
            self._load_library()

        seen_intids = set()
        seen_ntiids = set()
        ds = component.getUtility(IDataserver)
        with current_site(ds.dataserver_folder):
            for site in sites or ():
                solr_initializer = _SolrInitializer(batch_size,
                                                    site.__name__,
                                                    seen_intids,
                                                    seen_ntiids)
                solr_initializer.run(all_users=args.all_users,
                                     site_users=args.site_users,
                                     courses=args.courses,
                                     packages=args.packages)
        sys.exit()

    def __call__(self, *unused_args, **unused_kwargs):
        arg_parser = self.create_arg_parser()
        args = arg_parser.parse_args()

        env_dir = os.getenv('DATASERVER_DIR')
        if not env_dir or not os.path.exists(env_dir) and not os.path.isdir(env_dir):
            raise ValueError("Invalid dataserver environment root directory",
                             env_dir)

        conf_packages = ('nti.app.solr', 'nti.appserver', 'nti.dataserver',)
        context = create_context(env_dir, with_library=True, plugins=True)

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
