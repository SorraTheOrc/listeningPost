from django.conf.urls.defaults import *

urlpatterns = patterns('mailboxAnalysis.views',
    (r'^$', 'index'),
    
    (r'^configureImport$', 'configure_import'),
    (r'^startImport$', 'start_import'),

    (r'^participant/list$', 'list_participants'),
    (r'^participant/(?P<participant_id>\d+)/detail/$', 'participant_detail'),
    (r'^participant/(?P<participant_id>\d+)/emails/$', 'participant_emails'),
)
