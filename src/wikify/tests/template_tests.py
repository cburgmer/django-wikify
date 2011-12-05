import datetime

from lxml import html
import fudge

from django.utils import unittest
from django.test.client import RequestFactory
from django.shortcuts import render
from django.template import defaultfilters
from django.conf import settings
from django.core import paginator
from django import forms

from wikify.tests.utils import (construct_instance, construct_version,
                                construct_versions)

class PageForm(forms.Form):
    title = forms.CharField(max_length=255)
    content = forms.CharField()


class TemplateTestMixin(object):
    def assertHasElement(self, response, css_selector):
        doc = html.fromstring(response.content)
        elements = doc.cssselect(css_selector)

        self.assert_(len(elements) == 1, "Element %s not found" % css_selector)

    def assertHasNoElement(self, response, css_selector):
        doc = html.fromstring(response.content)
        elements = doc.cssselect(css_selector)

        self.assert_(len(elements) == 0, "Element %s found" % css_selector)


class EditTemplateTest(TemplateTestMixin, unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/test', {'action': 'edit'})

        self.template = 'wikify/edit.html'
        form = PageForm()
        self.context = {'form': form,
                        'object_id': 'test',
                        'version': None}

    def test_edit_template_has_save(self):
        response = render(self.request, self.template, self.context)

        self.assertHasElement(response, "button:contains('Save')")

    def test_edit_template_has_cancel(self):
        response = render(self.request, self.template, self.context)

        self.assertHasElement(response, "a:contains('Cancel')")

    def test_edit_template_has_form_fields(self):
        response = render(self.request, self.template, self.context)

        self.assertHasElement(response, "input[name='title']")
        self.assertHasElement(response, "input[name='content']")


class VersionTemplateTest(TemplateTestMixin, unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'wikify/version.html'

    def _prepare_request(self, version):
        instance  = version.object_version.object

        request = self.factory.get('/%s' % instance.pk,
                                   {'action': 'version',
                                    'version_id': version.id})

        fake_content_field = (fudge.Fake('Field')
                                   .has_attr(name='content')
                                   .has_attr(verbose_name='content'))
        # Workaround for fudge creating a callable fake that throws a runtime
        # error and Django not likeing that in its template guessing algorithm
        # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
        fake_content_field.is_callable().returns(fake_content_field)

        context = {'instance': instance,
                   'fields': [(fake_content_field, instance.content)],
                   'version': version}
        return request, context

    def test_version_template_has_content(self):
        version = construct_version()
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        instance = version.object_version.object

        self.assertHasElement(response, '.content')
        self.assertHasElement(response,
                              ".wikify-value:contains('%s')" % instance.content)

    def test_version_template_has_comment(self):
        comment = 'test comment'
        version = construct_version(comment=comment)
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')" % comment)

    def test_version_template_has_date_of_last_change(self):
        version = construct_version()
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        date = defaultfilters.date(version.revision.date_created,
                                   settings.DATETIME_FORMAT)
        self.assertHasElement(response,
                              ".wikify-date:contains('%s')" % date)

    def test_version_template_has_user_of_last_change(self):
        user_name = 'test user'
        version = construct_version(user_name=user_name)
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % user_name)

    def test_version_template_has_ip_of_last_change(self):
        ip_address = '127.0.0.1'
        version = construct_version(ip_address=ip_address)
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % ip_address)


class VersionsTemplateTest(TemplateTestMixin, unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'wikify/versions.html'

    def _prepare_request(self, object_id=None, versions=None, page=1):
        assert (not object_id or not versions
                or versions[-1].object_version.object.pk == object_id)

        object_id = object_id or versions[-1].object_version.object.pk
        request = self.factory.get('/%s' % object_id,
                                   {'action': 'versions'})

        p = paginator.Paginator(versions, 10)
        version_page = p.page(page)

        context = {'object_id': object_id,
                   'versions': version_page}
        return request, context

    def test_versions_template_has_entries(self):
        versions = construct_versions(version_count=2)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        # Make sure comments are different so we actually test something here
        assert versions[0].revision.comment != versions[1].revision.comment

        # Check for comments to distinguish versions
        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')"
                              % versions[0].revision.comment)
        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')"
                              % versions[1].revision.comment)

    def test_versions_template_has_change_time(self):
        versions = construct_versions(version_count=1)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        date = defaultfilters.date(versions[0].revision.date_created,
                                   settings.DATE_FORMAT)
        self.assertHasElement(response,
                              ".wikify-date:contains('%s')" % date)
        time = defaultfilters.date(versions[0].revision.date_created,
                                   settings.TIME_FORMAT)
        self.assertHasElement(response,
                              ".wikify-timestamp:contains('%s')" % time)

    def test_versions_template_has_author(self):
        user_name = 'test_user'
        versions = construct_versions(version_count=1,
                                            user_name=user_name)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % user_name)

    def test_versions_template_shows_ip_address(self):
        ip_address = '127.0.0.1'
        versions = construct_versions(version_count=1,
                                            ip_address=ip_address)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % ip_address)

    def test_versions_template_has_comment(self):
        versions = construct_versions(version_count=1)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')"
                              % versions[0].revision.comment)


    def test_versions_template_has_page_count(self):
        versions = construct_versions(version_count=30)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-current:contains('Page 1 of 3')")

    def test_versions_template_shows_next_page(self):
        versions = construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('next')")

    def test_versions_template_shows_previous_page(self):
        versions = construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions,
                                                 page=2)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('previous')")

    def test_versions_template_shows_no_next_when_on_last_page(self):
        versions = construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions,
                                                 page=2)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('next')")

    def test_versions_template_shows_no_previous_if_on_first_page(self):
        versions = construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('previous')")


class DiffTemplateTest(TemplateTestMixin, unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'wikify/diff.html'

    def _prepare_request(self, old_version, new_version, next_version=None):

        request = self.factory.get('/%s' % new_version.object_version.object.pk,
                                   {'action': 'diff',
                                    'version_id': new_version.id})

        fake_content_field = (fudge.Fake('Field')
                                   .has_attr(name='content')
                                   .has_attr(verbose_name='content'))
        # Workaround for fudge creating a callable fake that throws a runtime
        # error and Django not likeing that in its template guessing algorithm
        # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
        fake_content_field.is_callable().returns(fake_content_field)

        context = {'old_version': old_version,
                   'new_version': new_version,
                   'fields': [(fake_content_field,
                               old_version.object_version.object.content
                                   if old_version else None,
                               new_version.object_version.object.content)],
                   'next_version': next_version}
        return request, context

    def test_diff_template_has_content(self):
        old_version = construct_version(instance=construct_instance('test',
                                                                    'abcdefg'))
        new_version = construct_version(instance=construct_instance('test',
                                                                    '123456'))
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-content:contains('%s')"
                              % 'abcdefg')
        self.assertHasElement(response,
                              ".wikify-content:contains('%s')"
                              % '123456')

    def test_diff_template_has_change_date(self):
        old_version, new_version = construct_versions(version_count=2)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        old_date = defaultfilters.date(old_version.revision.date_created,
                                       settings.DATETIME_FORMAT)
        self.assertHasElement(response,
                              ".wikify-old .wikify-date:contains('%s')"
                              % old_date)
        new_date = defaultfilters.date(new_version.revision.date_created,
                                       settings.DATETIME_FORMAT)
        self.assertHasElement(response,
                              ".wikify-new .wikify-date:contains('%s')"
                              % new_date)

    def test_diff_template_has_users_of_changes(self):
        user_name1 = 'test user 1'
        old_version = construct_version(user_name=user_name1)
        user_name2 = 'test user 2'
        new_version = construct_version(user_name=user_name2)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-old .wikify-user:contains('%s')"
                              % user_name1)
        self.assertHasElement(response,
                              ".wikify-new .wikify-user:contains('%s')"
                              % user_name2)

    def test_diff_template_has_ip_of_changes(self):
        ip_address = '127.0.0.1'
        old_version, new_version = construct_versions(version_count=2,
                                                      ip_address=ip_address)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-old .wikify-user:contains('%s')"
                              % ip_address)
        self.assertHasElement(response,
                              ".wikify-new .wikify-user:contains('%s')"
                              % ip_address)

    def test_diff_template_has_comment(self):
        comment1 = 'test comment1'
        old_version = construct_version(comment=comment1)
        comment2 = 'test comment2'
        new_version = construct_version(comment=comment2)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-old .wikify-comment:contains('%s')"
                              % comment1)
        self.assertHasElement(response,
                              ".wikify-new .wikify-comment:contains('%s')"
                              % comment2)

    def test_diff_template_shows_next_version_link(self):
        old_version, new_version, next_version = construct_versions(
                                                                version_count=3)
        request, context = self._prepare_request(old_version,
                                                 new_version,
                                                 next_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('next')")

    def test_diff_template_shows_previous_version_link(self):
        old_version, new_version = construct_versions(version_count=2)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('previous')")

    def test_diff_template_shows_no_next_when_viewing_last_version(self):
        old_version, new_version = construct_versions(version_count=2)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('next')")

    def test_diff_template_shows_no_previous_if_viewing_first_version(self):
        new_version = construct_version()
        request, context = self._prepare_request(None, new_version)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('previous')")
