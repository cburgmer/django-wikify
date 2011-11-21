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

    def _construct_version(self, user_name=None, ip_address=None, comment=None,
                           instance=None, date_created=None):
        # Workaround for __str__ not being overwritable in Fudge!?
        # https://bitbucket.org/kumar303/fudge/issue/16/cannot-overwrite-fake-objects-__str__
        fake_user = (fudge.Fake('user').is_callable().returns(user_name)
                     if user_name else None)

        # Workaround for fudge creating a callable fake that throws a runtime
        # error and Django not likeing that in its template guessing algorithm
        # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
        if ip_address:
            fake_versionmeta_set = (fudge.Fake('versionmeta_set_helper')
                                         .is_callable()
                                         .returns(fudge.Fake('versionmeta_set')
                                                       .provides('get')
                                                       .returns(fudge.Fake('versionmeta')
                                                                      .has_attr(ip_address=ip_address))))
        else:
            fake_versionmeta_set = None

        date_created = date_created or datetime.datetime.utcnow()
        fake_revision = (fudge.Fake('revision')
                              .has_attr(user=fake_user)
                              .has_attr(versionmeta_set=fake_versionmeta_set)
                              .has_attr(date_created=date_created)
                              .has_attr(comment=comment))
        instance = instance or (fudge.Fake('page')
                                     .has_attr(pk='test title')
                                     .has_attr(content='test content'))

        version = (fudge.Fake('version')
                        .has_attr(id=42)
                        .has_attr(revision=fake_revision)
                        .has_attr(object_version=fudge.Fake()
                                                      .has_attr(object=instance)))

        # Workaround for fudge creating a callable fake that throws a runtime
        # error and Django not likeing that in its template guessing algorithm
        # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
        fake_revision.is_callable().returns(fake_revision)
        instance.is_callable().returns(instance)
        version.is_callable().returns(version)
        return version


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

        fake_content_field = (fudge.Fake('field')
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
        version = self._construct_version()
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        instance = version.object_version.object

        self.assertHasElement(response, '.content')
        self.assertHasElement(response,
                              ".wikify-value:contains('%s')" % instance.content)

    def test_version_template_has_comment(self):
        comment = 'test comment'
        version = self._construct_version(comment=comment)
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')" % comment)

    def test_version_template_has_date_of_last_change(self):
        version = self._construct_version()
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        date = defaultfilters.date(version.revision.date_created,
                                   settings.DATETIME_FORMAT)
        self.assertHasElement(response,
                              ".wikify-date:contains('%s')" % date)

    def test_version_template_has_user_of_last_change(self):
        user_name = 'test user'
        version = self._construct_version(user_name=user_name)
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % user_name)

    def test_version_template_has_ip_of_last_change(self):
        ip_address = '127.0.0.1'
        version = self._construct_version(ip_address=ip_address)
        request, context = self._prepare_request(version)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % ip_address)


class VersionsTemplateTest(TemplateTestMixin, unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.template = 'wikify/versions.html'

    def _construct_versions(self, version_count, user_name=None, ip_address=None):
        versions = []
        for i in range(version_count):
            instance = (fudge.Fake('page')
                             .has_attr(pk='test title')
                             .has_attr(content='content_%s' % i))
            date_created = (datetime.datetime.utcnow()
                            - datetime.timedelta(hours=i))
            version = self._construct_version(user_name=user_name,
                                              ip_address=ip_address,
                                              comment='Version %s' % i,
                                              instance=instance)
            versions.append(version)
        return versions

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
        versions = self._construct_versions(version_count=2)
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
        versions = self._construct_versions(version_count=1)
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
        versions = self._construct_versions(version_count=1,
                                            user_name=user_name)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % user_name)

    def test_versions_template_shows_ip_address(self):
        ip_address = '127.0.0.1'
        versions = self._construct_versions(version_count=1,
                                            ip_address=ip_address)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-user:contains('%s')" % ip_address)

    def test_versions_template_has_comment(self):
        versions = self._construct_versions(version_count=1)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-comment:contains('%s')"
                              % versions[0].revision.comment)


    def test_versions_template_has_page_count(self):
        versions = self._construct_versions(version_count=30)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              ".wikify-current:contains('Page 1 of 3')")

    def test_versions_template_shows_next_page(self):
        versions = self._construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('next')")

    def test_versions_template_shows_previous_page(self):
        versions = self._construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions,
                                                 page=2)
        response = render(request, self.template, context)

        self.assertHasElement(response,
                              "a:contains('previous')")

    def test_versions_template_shows_no_next_when_on_last_page(self):
        versions = self._construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions,
                                                 page=2)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('next')")

    def test_versions_template_shows_no_previous_if_on_first_page(self):
        versions = self._construct_versions(version_count=11)
        request, context = self._prepare_request(versions=versions)
        response = render(request, self.template, context)

        self.assertHasNoElement(response,
                                "a:contains('previous')")
