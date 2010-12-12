#!/bin/bash
# A script for resetting all databases to the default contents.
###############################################################
# WARNING
###############################################################
#
# Do not use this script on a production server.
# It will delete all your data
#
###############################################################
# WARNING
###############################################################

python manage.py reset mailboxAnalysis
python manage.py reset messageProcessingPlugin_Action
python manage.py reset helpdesk
python manage.py reset tagging

python manage.py syncdb
