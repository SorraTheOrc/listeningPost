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
    
    (r'^mailinglist/list$', 'mailinglist_list'),

    url(r'^mail/(?P<email_id>\d+)/read/$', 'email_detail', name='view_email'),
    (r'^mail/inbox/$', 'email_inbox'),
)
