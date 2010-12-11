""" 
-------------------------------------------------------------------------
Settings starting with A-Z will be imported, replacing default settings.
Settings starting with EXTRA_ will be appended to default settings.
-------------------------------------------------------------------------
"""

# Details of email account through which to send emails
EMAIL_USE_TLS = True
EMAIL_HOST = 'host.address.org'
EMAIL_HOST_USER = 'username'
EMAIL_HOST_PASSWORD = 'password'
EMAIL_PORT = 587

# Details of a POP3 account to retrieve emails from
# This account should be subscribed to any mailing lists you wish to track
SUBSCRIPTION_POP3_SERVER = "pop3.server.org"
SUBSCRIPTION_POP3_USER = "username"
SUBSCRIPTION_POP3_PASSWORD = "password"
SUBSCRIPTION_POP3_DELETE = False # set to true if you want listeningPost to delete emails

# Enabled plugins
EXTRA_INSTALLED_APPS = (
    'messageProcessingPlugin_Action',
)