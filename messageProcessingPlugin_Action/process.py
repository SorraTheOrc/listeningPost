from datetime import datetime
from mailboxAnalysis.models import Message
from messageProcessingPlugin_Action.models import ActionPattern
from helpdesk.models import Queue, Ticket
import re

def process(mail):
    """
    All Actionpatterns are 
    processed and, where they match, actions are created. If this
    message is in reply to another mail any outstanding reply action
    on that mail is marked as resolved. Finally, if no action has
    been created for this email then a reply action is created.
    """
    action_created = False
    patterns = ActionPattern.objects.filter(active = True)
    for pattern in patterns:
        create_action = True
        if pattern.subject_pattern:
            expr = re.compile(pattern.subject_pattern, re.IGNORECASE)
            if expr.match(mail.subject):
                create_action = True
            else:
                create_action = False
            
        if create_action and pattern.body_pattern:
            expr = re.compile(pattern.body_pattern, re.IGNORECASE)
            if expr.match(mail.body):
                create_action = True
            else:
                create_action = False
        
        if create_action and pattern.from_pattern:
            expr = re.compile(pattern.from_pattern, re.IGNORECASE)
            if expr.match(mail.fromParticipant):
                create_action = True
            else:
                create_action = False
                
        if create_action:
            ticket = Ticket(title = pattern.action_title,
                            description = pattern.action_description, 
                            queue = pattern.action_queue,
                            created = datetime.now(),
                            status = Ticket.OPEN_STATUS,
                            priority = pattern.action_priority)
            ticket.save()
            mail.action.add(ticket)
            action_created = True
    
    if not action_created:
        queue = Queue.objects.get(pk=1)
        # if this is in reply to another mail we already have, flag other mail as replied to
        if mail.backlink is not None:
            if Message.objects.filter(messageID = mail.backlink).count() > 0:
                repliedTo = Message.objects.filter(messageID = mail.backlink)[0]
                repliedTo.record_reply(instance)
        
        # if this mail doesn't already have a reply then set an action to check for one
        id = mail.messageID
        emails = Message.objects.all()
        replies = Message.objects.filter(backlink = id).count()
        if replies == 0:
            description = "Check that the email has received a reply if necessary."
            ticket = Ticket(title = "Reply needed for '" + mail.subject + "'",
                            description = description, 
                            queue = queue,
                            created = datetime.now(),
                            status = Ticket.OPEN_STATUS,
                            priority = 3)
            ticket.save()
            mail.action.add(ticket)