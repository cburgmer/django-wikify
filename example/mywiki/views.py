from django.shortcuts import render_to_response
from django.template import RequestContext

from wikify import wikify

from mywiki.models import Page

@wikify(Page)
def page(request, object_id):
    try:
        page = Page.objects.get(pk=object_id)
    except Page.DoesNotExist:
        page = None

    return render_to_response('page.html',
                              {'object_id': object_id,
                               'page': page},
                              context_instance=RequestContext(request))
