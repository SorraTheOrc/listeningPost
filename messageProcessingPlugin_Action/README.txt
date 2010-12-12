This is a message proccessing plugin. Like other such plugins all messages that are
imported into the system will be processed by this plugin. It's purpose is to create
actions based on patterns found in messages.

Use
===

Define regular expressions to be matched against the subject, body and from field
of a message. If all these expression are matched then a template action will be
created and attached to the message being processed.

To define the regular expressions and the action template simply add records to the
ActionPattern model.

Examples
========

These examples show the ActionPattern record in JSON format.

Naturally you will need to ensure the appropriate queues already exist in the
database.

Cast Vote
---------

A standard practice in Apache projects is to mark vote threads with [VOTE] at the
start of a subject line. This ActionPattern creates a vote action for any vote mail.
The action is not created for replies to the vote mails. This means that only a 
single vote action will be created for each vote thread.

  {
    "model": "messageProcessingPlugin_Action.ActionPattern",
    "fields": {
      "subject_pattern": "\\[VOTE\\].*",
      "action_title": "Cast vote",
      "action_queue": 2,
      "action_description": "Your vote is required on an issue",
      "action_priority": 1
    }
  }
  
Keyword Search
--------------

Search for a keyword in the body of an email and create an action to draw attention
to the issue.

  {
    "model": "messageProcessingPlugin_Actiotn.ActionPattern",
    "fields": {
      "body_pattern": ".*[\\s\\,\\.]+KEYWORD.*",
      "action_title": "Action required because contains KEYWORD",
      "action_queue": 1,
      "action_description": "This email contains the keyword 'KEYWORD' and is therefore marked for your priority attention.",
      "action_priority": 1
    }
  }
