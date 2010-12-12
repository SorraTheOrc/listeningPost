from django.conf.urls.defaults import *

urlpatterns = patterns('mailboxAnalysis.views',
    (r'^$', 'index'),
    
    (r'^configureImport$', 'configure_import'),
    (r'^startImport$', 'start_import'),

    (r'^participant/list$', 'list_participants'),
    (r'^participant/(?P<participant_id>\d+)/detail/$', 'participant_detail'),
    (r'^participant/(?P<participant_id>\d+)/emails/$', 'participant_emails'),
    (r'^participant/(?P<participant_id>\d+)/social/$', 'participant_social'),
    
    (r'^report$', 'report'),
    
    url(r'^mailinglist/list$', 'mailinglist_list', name='mailinglist_emails'),
    url(r'^mailinglist/(?P<list_id>\d+)/inbox/$', 'email_inbox', name="mailinglist_email"),

    url(r'^mail/(?P<email_id>\d+)/read/$', 'email_detail', name='view_email'),
    url(r'^mail/inbox/$', 'email_inbox', name="inbox"),
    url(r'^mail/(?P<email_id>\d+)/reply/$', 'email_reply', name='reply_email'),
    url(r'^mail/retrieve/$', 'email_retrieve', name='retrieve_email'),
    url(r'^mail/send/$', 'email_send', name='send_email'),
    
    url(r'ticket/list$', 'list_tickets', name="list_tickets"),
    url(r'ticket/(?P<ticket_id>\d+)/complete$', 'ticket_mark_complete', name="mark_ticket_complete"),
)
