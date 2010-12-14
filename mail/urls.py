from django.conf.urls.defaults import *

urlpatterns = patterns('mail.views',
    (r'^$', 'index'),

    url(r'^inbox/$', 'email_inbox', name="inbox"),
    url(r'^(?P<email_id>\d+)/read/$', 'email_detail', name='view_email'),
    url(r'^(?P<email_id>\d+)/reply/$', 'email_reply', name='reply_email'),
    
    url(r'^retrieve/$', 'email_retrieve', name='retrieve_email'),
    
    url(r'^ticket/list$', 'list_email_tickets', name="list_email_tickets"),
    url(r'^ticket/(?P<ticket_id>\d+)/complete$', 'ticket_mark_complete', name="mark_ticket_complete"),
)
