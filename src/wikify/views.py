from django.shortcuts import render_to_response
from django.http import HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.db import transaction
from django.core import paginator
from reversion.models import Version
from reversion import revision

from wikify.models import VersionMeta
from wikify.utils import get_model_wiki_form, model_field_iterator

def wikify(model):
    def decorator(func):
        def inner(request, *args, **kwargs):
            # The primary key must be either given by the model field's name, or
            #   simply by Django's standard 'object_id'
            primary_key = model._meta.pk.name
            object_id = kwargs.get(primary_key) or kwargs.get('object_id')

            # Get action
            if request.method == 'POST':
                action = request.POST.get('action')
            else:
                action = request.GET.get('action')

            if action == 'edit':
                return edit(request, model, object_id)
            elif action == 'version':
                return version(request, model, object_id)
            elif action == 'versions':
                return versions(request, model, object_id)
            else:
                # No valid action given, call decorated view
                return func(request, *args, **kwargs)

        return inner

    return decorator

@transaction.commit_on_success
def edit(request, model, object_id):
    """Edit or create a page."""

    form_class = get_model_wiki_form(model)
    version = None

    if request.method == 'POST':
        try:
            page = model.objects.get(pk=object_id)
        except model.DoesNotExist:
            page = model(pk=object_id)

        form = form_class(request.POST, instance=page)

        if form.is_valid():
            with revision:
                # Save the author, use our metadata model if user is anonymous
                if not request.user.is_anonymous():
                    revision.user = request.user
                else:
                    ip_address = request.META.get('HTTP_X_FORWARDED_FOR',
                                                request.META.get('REMOTE_ADDR'))
                    if ip_address:
                        revision.add_meta(VersionMeta,
                                          ip_address=ip_address)

                # Save a comment for the revision
                if form.cleaned_data.get('wikify_comment'):
                    revision.comment = form.cleaned_data['wikify_comment']

                form.save()

                # Successfully saved the page, now return to the 'read' view
                return HttpResponseRedirect(request.path)
    else:
        if request.GET.get('version_id'):
            # User is editing the page based on an older version
            try:
                version_id = int(request.GET.get('version_id'))
                version = (Version.objects.get_for_object_reference(model,
                                                                    object_id)
                                          .get(id=version_id))
                page = version.object_version.object
            except (ValueError, Version.DoesNotExist):
                raise Http404('Version not found')

            form = form_class(instance=page)
        else:
            try:
                page = model.objects.get(pk=object_id)
                form = form_class(instance=page)
            except model.DoesNotExist:
                form = form_class()

    return render_to_response('wikify/edit.html',
                              {'form': form,
                               'object_id': object_id,
                               'version': version},
                              context_instance=RequestContext(request))

def version(request, model, object_id):
    try:
        version_id = int(request.GET.get('version_id'))
        version = (Version.objects.get_for_object_reference(model, object_id)
                                  .get(id=version_id))
        instance = version.object_version.object
    except (ValueError, Version.DoesNotExist):
        raise Http404('Version not found')

    return render_to_response('wikify/version.html',
                              {'instance': instance,
                               'fields': list(model_field_iterator(instance)),
                               'version': version},
                              context_instance=RequestContext(request))

def versions(request, model, object_id, paginate=20):
    """Returns a paginated list of all versions of the given instance."""
    if not object_id:
        return HttpResponseBadRequest("Invalid title")

    all_versions = (Version.objects.get_for_object_reference(model, object_id)
                                   .reverse()
                                   .select_related("revision"))
    p = paginator.Paginator(all_versions, paginate)
    page_no = request.GET.get('page', 1)
    try:
        versions = p.page(page_no)
    except paginator.PageNotAnInteger:
        versions = p.page(1)
    except paginator.EmptyPage:
        versions = p.page(p.num_pages)

    return render_to_response('wikify/versions.html',
                              {'object_id': object_id,
                               'versions': versions,
                               'offset': p.count - versions.end_index()},
                              context_instance=RequestContext(request))
