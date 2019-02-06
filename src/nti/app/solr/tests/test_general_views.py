#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

# pylint: disable=protected-access,too-many-public-methods

import fudge

from hamcrest import assert_that
from hamcrest import has_length

from zope import component

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS

from nti.dataserver.tests import mock_dataserver

from nti.solr.interfaces import IIndexObjectEvent


class TestGeneralViews(ApplicationLayerTest):

    _events = ()

    def setUp(self):
        super(TestGeneralViews, self).setUp()
        self._events = []
        self._event_handler = lambda *args: self._events.append(args)
        gsm = component.getGlobalSiteManager()
        gsm.registerHandler(self._event_handler,
                            required=(IIndexObjectEvent,))

    def tearDown(self):
        gsm = component.getGlobalSiteManager()
        gsm.unregisterHandler(self._event_handler,
                              required=(IIndexObjectEvent,))
        super(TestGeneralViews, self).tearDown()

    @WithSharedApplicationMockDS(users=True, testapp=True)
    @fudge.patch('nti.app.solr.views.general_views.solr_notify')
    def test_index_users(self, mock_notify):
        mock_notify.is_callable().with_args().returns(None)

        url = '/dataserver2/solr/@@index_users'
        data = {
            'search': 'nothing'
        }
        self.testapp.post_json(url, data, status=204)

        data = {
            'username': self.default_username
        }
        self.testapp.post_json(url, data, status=204)

        self.testapp.post(url, status=204)

    @WithSharedApplicationMockDS(users=True, testapp=True)
    def test_index_users_by_site(self):
        assert_that(self._events, has_length(0))
        with mock_dataserver.mock_db_trans(self.ds, 'alpha.nextthought.com'):
            self._create_user(username='alphauser', external_value={'realname': u'alpha tester',
                                                                    'email': u'alpha@user.com'})

        url = '/dataserver2/solr/@@index_users'
        data = {
            'site': 'alpha.nextthought.com'
        }
        self.testapp.post_json(url, data, status=204)
        assert_that(self._events, has_length(1))
        self._events = []
        data['site'] = 'dne'
        self.testapp.post_json(url, data, status=204)
        assert_that(self._events, has_length(0))
