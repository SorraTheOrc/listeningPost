from django.conf.urls.defaults import *

# email views
urlpatterns = patterns('mail.views',
    (r'^$', 'index'),

    url(r'^inbox/$', 'email_inbox', name="inbox"),
    url(r'^send/$', 'email_send', name='send_email'),
    url(r'^(?P<email_id>\d+)/read/$', 'email_detail', name='view_email'),
    url(r'^(?P<email_id>\d+)/reply/$', 'email_reply', name='reply_email'),
    
    url(r'^retrieve/$', 'email_retrieve', name='retrieve_email'),
    
    url(r'^ticket/list$', 'list_email_tickets', name="list_email_tickets"),
    url(r'^ticket/(?P<ticket_id>\d+)/complete$', 'ticket_mark_complete', name="mark_ticket_complete"),
)

# participant views
urlpatterns += patterns('mail.views',
    url(r'^participant/list$', 'list_participants', name="participant_list"),
    url(r'^participant/(?P<participant_id>\d+)/detail/$', 'participant_detail', name="participant_detail"),
    url(r'^participant/(?P<participant_id>\d+)/emails/$', 'participant_emails', name="participant_emails"),
    
)

# Mailing list management
urlpatterns += patterns('mail.views',
    url(r'^mailinglist/list$', 'mailinglist_list', name='mailinglist_emails'),
    url(r'^mailinglist/(?P<list_id>\d+)/inbox/$', 'email_inbox', name="mailinglist_email"),
)