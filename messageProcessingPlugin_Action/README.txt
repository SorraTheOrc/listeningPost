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