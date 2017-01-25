#!/usr/bin/env python
"""
zope.generations installer for nti.app.products.ou

.. $Id$
"""

from __future__ import print_function, unicode_literals, absolute_import, division
__docformat__ = "restructuredtext en"

logger = __import__('logging').getLogger(__name__)

generation = 1

from zope import interface

from zope.generations.generations import SchemaManager as BaseSchemaManager

from zope.generations.interfaces import IInstallableSchemaManager


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


def evolve(context):
    pass
