import datetime

from lxml import html
import fudge

from django.utils import unittest
from django.test.client import RequestFactory
from django.shortcuts import render
from django.template import defaultfilters
from django.conf import settings
from django import forms


class PageForm(forms.Form):
    title = forms.CharField(max_length=255)
    content = forms.CharField()


class TemplateTestMixin(object):
    def assertHasElement(self, response, css_selector):
        doc = html.fromstring(response.content)
        elements = doc.cssselect(css_selector)

        self.assert_(len(elements) == 1, "Element %s not found" % css_selector)


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
        request = self.factory.get('/test',
                                   {'action': 'version',
                                    'version_id': version.id})

        instance  = version.object_version.object

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

    def _construct_version(self, user_name=None, ip_address=None, comment=None,
                           instance=None):
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

        fake_revision = (fudge.Fake('revision')
                              .has_attr(user=fake_user)
                              .has_attr(versionmeta_set=fake_versionmeta_set)
                              .has_attr(date_created=datetime.datetime.utcnow())
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
