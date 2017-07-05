#!/usr/bin/env python
# -*- coding: utf-8 -*
"""
.. $Id$
"""

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

from zope import interface

from zope.location.interfaces import ILocation

from z3c.autoinclude.zcml import includePluginsDirective

from nti.async.utils.processor import Processor

from nti.dataserver.utils.base_script import create_context

from nti.solr import QUEUE_NAMES


@interface.implementer(ILocation)
class PluginPoint(object):
    __parent__ = None

    def __init__(self, name):
        self.__name__ = name
PP_SOLR = PluginPoint('nti.solr')


class Constructor(Processor):

    def set_log_formatter(self, args):
        super(Constructor, self).set_log_formatter(args)

    def extend_context(self, context):
        includePluginsDirective(context, PP_SOLR)

    def create_context(self, env_dir, args=None):
        context = create_context(env_dir, with_library=True,
                                 plugins=False,
                                 slugs=True,
                                 slugs_files=("*solr.zcml", "*features.zcml"))
        self.extend_context(context)
        return context

    def conf_packages(self):
        return (self.conf_package, 'nti.app.solr', 'nti.async')

    def process_args(self, args):
        setattr(args, 'redis', True)
        setattr(args, 'library', True)  # load library
        setattr(args, 'max_sleep_time', 30)
        setattr(args, 'queue_names', QUEUE_NAMES)
        super(Constructor, self).process_args(args)


def main():
    return Constructor()()

if __name__ == '__main__':
    main()
