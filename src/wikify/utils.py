from django import forms
from django.forms.models import modelform_factory
from django.utils.translation import ugettext_lazy

def get_model_primary_field(model):
    """Returns the field name of the model's primary key."""

    return model._meta.fields[model._meta.pk_index()].name

def get_model_wiki_form(model):
    """Creates a form for the given model, excluding the primary key."""

    primary_key_field = get_model_primary_field(model)

    # Create the model form and exclude the primary key
    form_class = modelform_factory(model, exclude=(primary_key_field,))

    # Add a comment widget
    comment_widget = forms.TextInput(
                          attrs={'placeholder': ugettext_lazy("Add a comment")})
    comment_field = forms.CharField(widget=comment_widget,
                                    required=False,
                                    label=ugettext_lazy("Comment"))
    form_class.base_fields['wikify_comment'] = comment_field
    return form_class
