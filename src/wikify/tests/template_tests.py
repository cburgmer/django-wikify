import datetime

from lxml import html
import fudge

from django.utils import unittest
from django.test.client import RequestFactory
from django.shortcuts import render
from django.template import defaultfilters
from django.conf import settings
from django.core import paginator
from django.db import models
from django.forms.models import modelform_factory
from django.contrib.auth.models import User
import reversion

from wikify.models import VersionMeta

try:
    from wikify.diff_utils import side_by_side_diff, context_diff
except ImportError:
    can_test_diff = False
else:
    can_test_diff = True

# App environment

class Page(models.Model):
    title = models.CharField(max_length=255, primary_key=True)
    content = models.TextField(blank=True)

    class Meta:
        # Hack: Cannot use an app_label that is under South control, due to http://south.aeracode.org/ticket/520
        app_label = "auth"


# Helpers

page_pk_counter = 0;

def get_unique_page_title():
    global page_pk_counter
    page_pk_counter += 1;
    return "test title %d" % page_pk_counter


def construct_versions(version_count):
    assert version_count > 0

    with reversion.revision:
        instance = Page.objects.create(title=get_unique_page_title(),
                                       content="content_0")
        reversion.revision.comment = 'Version 0'

    versions = []
    for i in range(1, version_count):
        with reversion.revision:
            instance.content = "content_%s" % i
            instance.save()
            reversion.revision.comment = 'Version %s' % i

    return reversion.get_for_object_reference(Page, instance.pk).order_by("pk")

# Tests

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

        self.instance = Page(title="test title", content="test content")
        form_class = modelform_factory(Page)
        form = form_class(instance=self.instance)

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

        self.assertHasElement(response,
                              "input[name='title'][value='%s']"
                              % self.instance.title)
        self.assertHasElement(response,
                              "textarea[name='content']:contains('%s')"
                              % self.instance.content)


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
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
        version = reversion.get_for_object_reference(Page, instance.pk)[0]

        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        instance = version.object_version.object

        self.assertHasElement(response, '.content')
        self.assertHasElement(response,
                              ".wikify-value:contains('%s')" % instance.content)

    def test_version_template_has_comment(self):
        comment = 'test comment'
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.comment = comment
        version = reversion.get_for_object_reference(Page, instance.pk)[0]

        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')" % comment)

    def test_version_template_has_date_of_last_change(self):
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
        version = reversion.get_for_object_reference(Page, instance.pk)[0]

        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        date = defaultfilters.date(version.revision.date_created,
                                   settings.DATETIME_FORMAT)
        self.assertHasElement(response,
                              ".wikify-date:contains('%s')" % date)

    def test_version_template_has_user_of_last_change(self):
        user = User.objects.create(username='test user')
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.user = user
        version = reversion.get_for_object_reference(Page, instance.pk)[0]

        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % 'test user')

    def test_version_template_has_ip_of_last_change(self):
        ip_address = '127.0.0.1'
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.add_meta(VersionMeta,
                                        ip_address=ip_address)
        version = reversion.get_for_object_reference(Page, instance.pk)[0]

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
                or list(versions)[-1].object_version.object.pk == object_id)

        object_id = object_id or list(versions)[-1].object_version.object.pk
        request = self.factory.get('/%s' % object_id,
                                   {'action': 'versions'})

        p = paginator.Paginator(versions, 10)
        version_page = p.page(page)

        context = {'object_id': object_id,
                   'versions': version_page}
        return request, context

    def test_versions_template_has_entries(self):
        versions = construct_versions(2)
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
        versions = construct_versions(1)
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
        user = User.objects.create(username='test_user')
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.user = user
        version = reversion.get_for_object_reference(Page, instance.pk)[0]

        request, context = self._prepare_request(versions=[version])
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % user.username)

    def test_versions_template_shows_ip_address(self):
        ip_address = '127.0.0.1'
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.add_meta(VersionMeta,
                                        ip_address=ip_address)
        version = reversion.get_for_object_reference(Page, instance.pk)[0]

        request, context = self._prepare_request(versions=[version])
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % ip_address)

    def test_versions_template_has_comment(self):
        versions = construct_versions(1)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')"
                              % versions[0].revision.comment)


    def test_versions_template_has_page_count(self):
        versions = construct_versions(30)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-current:contains('Page 1 of 3')")

    def test_versions_template_shows_next_page(self):
        versions = construct_versions(11)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('next')")

    def test_versions_template_shows_previous_page(self):
        versions = construct_versions(11)
        request, context = self._prepare_request(versions=versions,
                                                 page=2)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('previous')")

    def test_versions_template_shows_no_next_when_on_last_page(self):
        versions = construct_versions(11)
        request, context = self._prepare_request(versions=versions,
                                                 page=2)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('next')")

    def test_versions_template_shows_no_previous_if_on_first_page(self):
        versions = construct_versions(11)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('previous')")


@unittest.skipUnless(can_test_diff, "Diff match patch library not installed")
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
        with reversion.revision:
            instance = Page.objects.create(title="some title",
                                           content='abcdefg')
        with reversion.revision:
            instance.content = '123456'
            instance.save()

        new_version, old_version = reversion.get_for_object_reference(Page,
                                                                    instance.pk)

        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-content del:contains('%s')"
                              % 'abcdefg')
        self.assertHasElement(response,
                              ".wikify-content ins:contains('%s')"
                              % '123456')

    def test_diff_template_has_change_date(self):
        old_version, new_version = construct_versions(2)
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
        user1 = User.objects.create(username='test user 1')
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.user = user1

        user2 = User.objects.create(username='test user 2')
        with reversion.revision:
            instance.content = "changed test content"
            instance.save()
            reversion.revision.user = user2

        new_version, old_version = reversion.get_for_object_reference(Page,
                                                                    instance.pk)

        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-old .wikify-user:contains('%s')"
                              % user1.username)
        self.assertHasElement(response,
                              ".wikify-new .wikify-user:contains('%s')"
                              % user2.username)

    def test_diff_template_has_ip_of_changes(self):
        ip_address = '127.0.0.1'
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.add_meta(VersionMeta,
                                        ip_address=ip_address)
        with reversion.revision:
            instance.content = "changed test content"
            instance.save()
            reversion.revision.add_meta(VersionMeta,
                                        ip_address=ip_address)
        new_version, old_version = reversion.get_for_object_reference(Page,
                                                                    instance.pk)

        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-old .wikify-user:contains('%s')"
                              % ip_address)
        self.assertHasElement(response,
                              ".wikify-new .wikify-user:contains('%s')"
                              % ip_address)

    def test_diff_template_has_comment(self):
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
            reversion.revision.comment = 'test comment1'

        with reversion.revision:
            instance.content = "changed test content"
            instance.save()
            reversion.revision.comment = 'test comment2'

        new_version, old_version = reversion.get_for_object_reference(Page,
                                                                    instance.pk)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-old .wikify-comment:contains('%s')"
                              % "test comment1")
        self.assertHasElement(response,
                              ".wikify-new .wikify-comment:contains('%s')"
                              % "test comment2")

    def test_diff_template_shows_next_version_link(self):
        old_version, new_version, next_version = construct_versions(3)
        request, context = self._prepare_request(old_version,
                                                 new_version,
                                                 next_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('next')")

    def test_diff_template_shows_previous_version_link(self):
        old_version, new_version = construct_versions(2)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('previous')")

    def test_diff_template_shows_no_next_when_viewing_last_version(self):
        old_version, new_version = construct_versions(2)
        request, context = self._prepare_request(old_version, new_version)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('next')")

    def test_diff_template_shows_no_previous_if_viewing_first_version(self):
        with reversion.revision:
            instance = Page.objects.create(title=get_unique_page_title(),
                                           content="test content")
        new_version = reversion.get_for_object_reference(Page, instance.pk)[0]

        request, context = self._prepare_request(None, new_version)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('previous')")
