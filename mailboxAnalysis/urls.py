from django.conf.urls.defaults import *

urlpatterns = patterns('mailboxAnalysis.views',
    (r'^$', 'index'),
    
    (r'^configureImport$', 'configure_import'),
    (r'^startImport$', 'start_import'),

    url(r'^participant/(?P<participant_id>\d+)/social/$', 'social_graph', name="social_graph"),
    
    (r'^report$', 'report'),
)

