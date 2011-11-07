from lxml import html

from django.utils import unittest
from django.test.client import RequestFactory
from django.shortcuts import render
from django import forms


class PageForm(forms.Form):
    title = forms.CharField(max_length=255)
    content = forms.CharField()


class EditTemplateTest(unittest.TestCase):
    def assertHasElement(self, response, css_selector):
        doc = html.fromstring(response.content)
        elements = doc.cssselect(css_selector)

        self.assert_(len(elements) == 1, "Element %s not found" % css_selector)

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
