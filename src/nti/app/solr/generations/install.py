#!/usr/bin/env python
"""
.. $Id$
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from zope import interface

from zope.generations.generations import SchemaManager as BaseSchemaManager

from zope.generations.interfaces import IInstallableSchemaManager

generation = 8

logger = __import__('logging').getLogger(__name__)


@interface.implementer(IInstallableSchemaManager)
class SOLRSchemaManager(BaseSchemaManager):
    """
    A schema manager that we can register as a utility in ZCML.
    """

    def __init__(self):
        super(SOLRSchemaManager, self).__init__(
            generation=generation,
            minimum_generation=generation,
            package_name='nti.app.solr.generations')


def evolve(unused_context):
    pass
