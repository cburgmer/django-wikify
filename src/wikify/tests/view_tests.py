import fudge

from django.test import TestCase
from django.db import models
from django.http import HttpResponse
from django.conf.urls.defaults import patterns
import reversion

from wikify.tests.utils import construct_version, construct_versions
from wikify import wikify

class Page(models.Model):
    title = models.CharField(max_length=255, primary_key=True)
    content = models.TextField(blank=True)

    def __unicode__(self):
        return self.title

reversion.register(Page)

@wikify(Page)
def page_view(request, object_id):
    try:
        page = Page.objects.get(pk=object_id)
    except Page.DoesNotExist:
        page = None

    return HttpResponse("OK")

urlpatterns = patterns("",

    (r'^(?P<object_id>[^/]+)$', page_view),

)

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
