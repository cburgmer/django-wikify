from django.conf.urls.defaults import *
from django.views.generic import RedirectView

from mywiki.views import page

urlpatterns = patterns('',
    (r'^(?P<object_id>[^/]+)$', page),
    # 'Main' is default landing page
    (r'^$', RedirectView.as_view(url='Main')),
)
