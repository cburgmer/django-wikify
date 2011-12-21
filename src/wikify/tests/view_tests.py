from urllib2 import urlparse
import fudge
import unittest

from django.test import TestCase
from django.db import models
from django.http import HttpResponse
from django.conf.urls.defaults import patterns
import reversion

from wikify.tests.utils import (construct_instance, construct_version,
                                construct_versions)
from wikify import wikify

try:
    from wikify.diff_utils import side_by_side_diff, context_diff
except ImportError:
    can_test_diff = False
else:
    can_test_diff = True

class Page(models.Model):
    title = models.CharField(max_length=255, primary_key=True)
    content = models.TextField(blank=True)

    def __unicode__(self):
        return self.title

reversion.register(Page)

@wikify('wikify.tests.Page')
def page_view(request, object_id):
    try:
        page = Page.objects.get(pk=object_id)
    except Page.DoesNotExist:
        page = None

    return HttpResponse("OK")

urlpatterns = patterns("",

    (r'^(?P<object_id>[^/]+)$', page_view),

)

class EditViewTest(TestCase):

    urls = 'wikify.tests'

    @fudge.patch('wikify.tests.Page.objects')
    @fudge.patch('wikify.utils.get_model_wiki_form')
    def test_edit_view_renders_form_on_existing_instance(self, page_manager,
                                                         get_model_wiki_form):
        instance = construct_instance('test title', 'test content')

        page_manager.expects('get').with_args(pk=instance.pk).returns(instance)
        fake_form = "fake form"
        (get_model_wiki_form.is_callable()
                            .returns_fake().is_callable()
                                           .with_args(instance=instance)
                                           .returns(fake_form))

        resp = self.client.get('/%s' % instance.pk, {'action': 'edit'})

        self.assertEquals(resp.status_code, 200)
        self.assertIn('wikify/edit.html',
                      [template.name for template in resp.templates])

        self.assertEquals(fake_form, resp.context['form'])
        self.assertEquals(instance.pk, resp.context['object_id'])
        self.assertEquals(None, resp.context['version'])

    @fudge.patch('wikify.tests.Page.objects')
    @fudge.patch('wikify.utils.get_model_wiki_form')
    def test_edit_view_renders_form_for_creating_an_instance(self, page_manager,
                                                           get_model_wiki_form):

        object_id = "non existing item"
        (page_manager.expects('get').with_args(pk=object_id)
                                    .raises(Page.DoesNotExist))
        fake_form = "fake form"
        (get_model_wiki_form.is_callable()
                            .returns_fake().is_callable()
                                           .returns(fake_form))

        resp = self.client.get('/%s' % object_id, {'action': 'edit'})

        self.assertEquals(resp.status_code, 200)
        self.assertIn('wikify/edit.html',
                      [template.name for template in resp.templates])

        self.assertEquals(fake_form, resp.context['form'])
        self.assertEquals(object_id, resp.context['object_id'])
        self.assertEquals(None, resp.context['version'])

    @fudge.patch('wikify.tests.Page.objects')
    @fudge.patch('reversion.models.Version.objects')
    @fudge.patch('wikify.utils.get_model_wiki_form')
    def test_edit_view_renders_form_for_instance_version(self,
                                                         page_manager,
                                                         version_manager,
                                                         get_model_wiki_form):

        version = construct_version()
        instance = version.object_version.object
        (version_manager.expects('get_for_object_reference')
                        .with_args(Page, instance.pk)
                        .returns_fake().expects('get')
                                       .with_args(id=42)
                                       .returns(version))
        fake_form = "fake form"
        (get_model_wiki_form.is_callable()
                            .returns_fake().is_callable()
                                           .returns(fake_form))

        resp = self.client.get('/%s' % instance.pk,
                               {'action': 'edit', 'version_id': '42'})

        self.assertEquals(resp.status_code, 200)
        self.assertIn('wikify/edit.html',
                      [template.name for template in resp.templates])

        self.assertEquals(fake_form, resp.context['form'])
        self.assertEquals(instance.pk, resp.context['object_id'])
        self.assertEquals(version, resp.context['version'])

    @fudge.patch('wikify.tests.Page.objects')
    @fudge.patch('wikify.utils.get_model_wiki_form')
    def test_edit_view_creates_a_new_instance(self, page_manager,
                                              get_model_wiki_form):

        object_id = "non existing item"
        (page_manager.expects('get').with_args(pk=object_id)
                                    .raises(Page.DoesNotExist))

        cleaned_data = fudge.Fake('CleanedData').provides('get').returns(None)
        fake_form = (fudge.Fake('Form').expects('is_valid').returns(True)
                                       .expects('save')
                                       .has_attr(cleaned_data=cleaned_data))
        (get_model_wiki_form.is_callable()
                            .returns_fake().is_callable()
                                           .returns(fake_form))

        resp = self.client.post('/%s' % object_id, {'action': 'edit'})

        self.assertEquals(resp.status_code, 302)
        location = urlparse.urlsplit(resp['location']).path
        self.assertEquals(urlparse.unquote(location),
                          '/%s' % object_id)

    @fudge.patch('wikify.tests.Page.objects')
    @fudge.patch('wikify.utils.get_model_wiki_form')
    def test_edit_view_saves_an_existing_instance(self, page_manager,
                                                  get_model_wiki_form):

        instance = construct_instance('test title', 'test content')
        (page_manager.expects('get').with_args(pk=instance.pk)
                                    .returns(instance))

        cleaned_data = fudge.Fake('CleanedData').provides('get').returns(None)
        fake_form = (fudge.Fake('Form').expects('is_valid').returns(True)
                                       .expects('save')
                                       .has_attr(cleaned_data=cleaned_data))
        (get_model_wiki_form.is_callable()
                            .returns_fake().is_callable()
                                           .returns(fake_form))

        resp = self.client.post('/%s' % instance.pk, {'action': 'edit'})

        self.assertEquals(resp.status_code, 302)
        location = urlparse.urlsplit(resp['location']).path
        self.assertEquals(urlparse.unquote(location),
                          '/%s' % instance.pk)

# TODO
# test that comment is saved
# test invalid form
# test that anonymous user's IP is saved
# test that a new version is created

class VersionViewTest(TestCase):

    urls = 'wikify.tests'

    @fudge.patch('reversion.models.Version')
    def test_version_view(self, Version):
        version = construct_version()
        instance = version.object_version.object

        fake_versionmanager = fudge.Fake('VersionManager')
        (fake_versionmanager.expects('get_for_object_reference')
                            .returns_fake(name='QuerySet')
                            .expects('get')
                            .with_args(id=version.id)
                            .returns(version))
        Version.has_attr(objects=fake_versionmanager)
        resp = self.client.get('/%s' % instance.pk,
                               {'action': 'version', 'version_id': version.id})

        self.assertEquals(resp.status_code, 200)
        self.assertIn('wikify/version.html',
                      [template.name for template in resp.templates])

        self.assertEquals(instance, resp.context['instance'])
        self.assertEquals(version, resp.context['version'])
        self.assertEquals(len(resp.context['fields']), 1)
        _, field_value = resp.context['fields'][0]
        self.assertEquals(instance.content, field_value)

    def test_version_view_returns_400_for_invalid_version(self):
        resp = self.client.get('/test',
                               {'action': 'version', 'version_id': 'a42'})
        self.assertEquals(resp.status_code, 404)

    def test_version_view_returns_400_for_missing_version(self):
        resp = self.client.get('/test',
                               {'action': 'version', 'version_id': '42'})
        self.assertEquals(resp.status_code, 404)


class VersionsViewTest(TestCase):

    urls = 'wikify.tests'

    @fudge.patch('reversion.models.Version')
    def test_versions_view(self, Version):
        versions = construct_versions(version_count=2)
        instance = versions[0].object_version.object

        fake_versionmanager = fudge.Fake('VersionManager')
        (fake_versionmanager.expects('get_for_object_reference')
                            .returns_fake(name='QuerySet')
                            .provides('reverse')
                            .returns_fake(name='QuerySet')
                            .provides('select_related')
                            .returns(versions))
        Version.has_attr(objects=fake_versionmanager)
        resp = self.client.get('/%s' % instance.pk,
                               {'action': 'versions'})

        self.assertEquals(resp.status_code, 200)
        self.assertIn('wikify/versions.html',
                      [template.name for template in resp.templates])

        self.assertEquals(instance.pk, resp.context['object_id'])
        self.assertEquals(versions, resp.context['versions'].object_list)

    @fudge.patch('reversion.models.Version')
    def test_versions_view_shows_paged_results(self, Version):
        versions = construct_versions(version_count=40)
        instance = versions[0].object_version.object

        fake_versionmanager = fudge.Fake('VersionManager')
        (fake_versionmanager.expects('get_for_object_reference')
                            .returns_fake(name='QuerySet')
                            .provides('reverse')
                            .returns_fake(name='QuerySet')
                            .provides('select_related')
                            .returns(versions))
        Version.has_attr(objects=fake_versionmanager)
        resp = self.client.get('/%s' % instance.pk,
                               {'action': 'versions'})

        self.assertEquals(resp.status_code, 200)

        self.assertEquals(versions[:20], resp.context['versions'].object_list)

    @fudge.patch('reversion.models.Version')
    def test_versions_view_shows_second_page(self, Version):
        versions = construct_versions(version_count=40)
        instance = versions[0].object_version.object

        fake_versionmanager = fudge.Fake('VersionManager')
        (fake_versionmanager.expects('get_for_object_reference')
                            .returns_fake(name='QuerySet')
                            .provides('reverse')
                            .returns_fake(name='QuerySet')
                            .provides('select_related')
                            .returns(versions))
        Version.has_attr(objects=fake_versionmanager)
        resp = self.client.get('/%s' % instance.pk,
                               {'action': 'versions', 'page': '2'})

        self.assertEquals(resp.status_code, 200)

        self.assertEquals(versions[20:], resp.context['versions'].object_list)


@unittest.skipUnless(can_test_diff, "Diff match patch library not installed")
class DiffViewTest(TestCase):

    urls = 'wikify.tests'

    @fudge.patch('reversion.models.Version')
    def test_versions_view(self, Version):
        old, new, next = construct_versions(version_count=3)
        old_instance = old.object_version.object
        new_instance = new.object_version.object

        fake_queryset = fudge.Fake('QuerySet')
        (fake_queryset.expects('get')
                      .with_args(id=new.id)
                      .returns(new))
        (fake_queryset.expects('filter')
                      .with_args(id__lt=new.id)
                      .returns_fake(name='QuerySet')
                      .provides('reverse')
                      .returns([old]))
        (fake_queryset.expects('filter')
                      .with_args(id__gt=new.id)
                      .returns([next]))

        Version.has_attr(objects=fudge.Fake('VersionManager')
                                      .expects('get_for_object_reference')
                                      .returns(fake_queryset))
        resp = self.client.get('/%s' % old_instance.pk,
                               {'action': 'diff',
                                'version_id': str(new.id)})

        self.assertEquals(resp.status_code, 200)
        self.assertIn('wikify/diff.html',
                      [template.name for template in resp.templates])

        self.assertEquals(old, resp.context['old_version'])
        self.assertEquals(new, resp.context['new_version'])
        self.assertEquals(next, resp.context['next_version'])

        self.assertEquals(len(resp.context['fields']), 1)
        _, old_value, new_value = resp.context['fields'][0]
        self.assertEquals(old_instance.content, old_value)
        self.assertEquals(new_instance.content, new_value)

    @fudge.patch('reversion.models.Version')
    def test_diff_view_for_single_version(self, Version):
        new = construct_version()
        new_instance = new.object_version.object

        fake_queryset = fudge.Fake('QuerySet')
        (fake_queryset.expects('get')
                      .with_args(id=new.id)
                      .returns(new))
        (fake_queryset.expects('filter')
                      .with_args(id__lt=new.id)
                      .returns_fake(name='QuerySet')
                      .provides('reverse')
                      .returns([]))
        (fake_queryset.expects('filter')
                      .with_args(id__gt=new.id)
                      .returns([]))

        Version.has_attr(objects=fudge.Fake('VersionManager')
                                      .expects('get_for_object_reference')
                                      .returns(fake_queryset))
        resp = self.client.get('/%s' % new_instance.pk,
                               {'action': 'diff',
                                'version_id': str(new.id)})

        self.assertEquals(resp.status_code, 200)
        self.assertIn('wikify/diff.html',
                      [template.name for template in resp.templates])

        self.assertEquals(None, resp.context['old_version'])
        self.assertEquals(new, resp.context['new_version'])
        self.assertEquals(None, resp.context['next_version'])

        self.assertEquals(len(resp.context['fields']), 1)
        _, old_value, new_value = resp.context['fields'][0]
        self.assertEquals(None, old_value)
        self.assertEquals(new_instance.content, new_value)

    def test_diff_view_returns_400_for_invalid_version(self):
        resp = self.client.get('/test',
                               {'action': 'diff', 'version_id': 'a42'})
        self.assertEquals(resp.status_code, 404)

    def test_diff_view_returns_400_for_missing_version(self):
        resp = self.client.get('/test',
                               {'action': 'diff', 'version_id': '42'})
        self.assertEquals(resp.status_code, 404)
