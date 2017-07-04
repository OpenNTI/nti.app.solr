#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
__docformat__ = "restructuredtext en"

# disable: accessing protected members, too many methods
# pylint: disable=W0212,R0904

from hamcrest import is_not
does_not = is_not

import fudge

from nti.app.testing.application_webtest import ApplicationLayerTest

from nti.app.testing.decorators import WithSharedApplicationMockDS


class TestAdminViews(ApplicationLayerTest):

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