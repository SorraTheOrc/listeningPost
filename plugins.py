"""
Configure and enable plugins that are to be used in the application.
This file can be overridden by creating a local_plugins.py file that
implements all the methods in this one.
"""

def processPlugins(mail):
    from messageProcessingPlugin_Action import process as createAction
    createAction.process(mail)