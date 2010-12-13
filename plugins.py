"""
Configure and enable plugins that are to be used in the application.
This file can be overridden by creating a local_plugins.py file that
implements all the methods in this one.
"""
from messageProcessingPlugin_Action import process as createAction
from messageProcessingPlugin_TextWrap import process as bodywrap

def processPlugins(mail):
    bodywrap.process(mail)
    createAction.process(mail)
    