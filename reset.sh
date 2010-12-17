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

echo "reset mailboxAnalysis"
python manage.py reset mailboxAnalysis

echo "reset messageProcesingPlugin_Action"
python manage.py reset messageProcessingPlugin_Action

echo "reset menu"
python manage.py reset menu

echo "reset helpdesk"
python manage.py reset helpdesk

echo "reset tagging"
python manage.py reset tagging

python manage.py syncdb
