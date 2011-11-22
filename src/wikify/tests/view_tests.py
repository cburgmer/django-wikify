import fudge

from django.test import TestCase

from wikify.tests.utils import construct_version

class VersionViewTest(TestCase):
    @fudge.patch('reversion.models.Version')
    def test_version_view(self, Version):
        version = construct_version()
        instance = version.object_version.object

        Version.has_attr(objects=fudge.Fake()
                                      .expects('get_for_object_reference')
                                      .returns(fudge.Fake()
                                                    .expects('get')
                                                    .with_args(id=version.id)
                                                    .returns(version)))
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
