from django.shortcuts import render_to_response
from django.http import HttpResponseBadRequest, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.db import transaction
from django.core import paginator
from reversion import models
from reversion import revision

from wikify.models import VersionMeta
from wikify import utils

@transaction.commit_on_success
def edit(request, model, object_id):
    """Edit or create a page."""

    form_class = utils.get_model_wiki_form(model)
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
                version = (models.Version.objects.get_for_object_reference(
                                                               model, object_id)
                                         .get(id=version_id))
                page = version.object_version.object
            except (ValueError, models.Version.DoesNotExist):
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
    """Returns a versioned view of the given instance."""
    try:
        version_id = int(request.GET.get('version_id'))
        version = (models.Version.objects.get_for_object_reference(model,
                                                                   object_id)
                                  .get(id=version_id))
        instance = version.object_version.object
    except (ValueError, models.Version.DoesNotExist):
        raise Http404('Version not found')

    return render_to_response('wikify/version.html',
                              {'instance': instance,
                               'fields': list(utils.model_field_iterator(
                                                                     instance)),
                               'version': version},
                              context_instance=RequestContext(request))

def versions(request, model, object_id, paginate=20):
    """Returns a paginated list of all versions of the given instance."""

    all_versions = (models.Version.objects.get_for_object_reference(model,
                                                                    object_id)
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
                               'versions': versions},
                              context_instance=RequestContext(request))

def diff(request, model, object_id):
    """Returns the difference between the given version and the previous one."""

    versions = models.Version.objects.get_for_object_reference(model, object_id)
    try:
        version_id = int(request.GET.get('version_id'))
        # Get version and make sure it belongs to the given page
        new_version = versions.get(id=version_id)
    except (ValueError, models.Version.DoesNotExist):
        raise Http404("Version not found")

    old_version_q = versions.filter(id__lt=version_id).reverse()
    old_version = old_version_q[0] if old_version_q else None

    # Get the next version so we can provide a link
    next_version_q = versions.filter(id__gt=version_id)
    next_version = next_version_q[0] if next_version_q else None

    context = {'old_version': old_version,
               'new_version': new_version,
               'fields': list(utils.version_field_iterator(old_version,
                                                           new_version)),
               'next_version': next_version}
    return render_to_response('wikify/diff.html',
                              context,
                              context_instance=RequestContext(request))
