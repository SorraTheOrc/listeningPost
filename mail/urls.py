from django.conf.urls.defaults import *

urlpatterns = patterns('mail.views',
    (r'^$', 'index'),

    url(r'^inbox/$', 'email_inbox', name="inbox"),
    url(r'^(?P<email_id>\d+)/read/$', 'email_detail', name='view_email'),
   
)
