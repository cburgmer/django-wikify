from django.conf.urls import patterns
from django.views.generic import RedirectView

from mywiki.views import page

urlpatterns = patterns('',
    (r'^(?P<object_id>[^/]+)$', page),
    # 'Main' is default landing page
    (r'^$', RedirectView.as_view(url='Main')),
)
