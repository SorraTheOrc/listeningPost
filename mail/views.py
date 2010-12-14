import email.Utils, poplib, re, string, time

from datetime import datetime, timedelta

from django.conf import settings
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import redirect, render_to_response, get_object_or_404

from helpdesk.models import FollowUp, Queue, Ticket

from mailboxAnalysis.views import add_main_menu
from mailboxAnalysis.models import Archive
from mailboxAnalysis.models import Message
from mailboxAnalysis.models import Maillist
from mailboxAnalysis.models import Participant

try:
  import local_plugins as plugins
except ImportError:
  import plugins

def _paginate(request, object_list):
    paginator = Paginator(object_list, 15)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    
    try:
        emails = paginator.page(page)
    except (EmptyPage, InvalidPage):
        emails = paginator.page(paginator.num_pages)
    
    return emails


def index(request):
    return redirect("email_inbox")
    
def email_inbox(request, list_id=None):
  """
  Create a list of all emails in an inbox. An inbox is either all mail for a 
  user (default) or all email in a list (when list_id is provived)
  """
  if list_id is None:
      email_list = Message.objects.all()
  else:
      email_list = Message.objects.filter(list=list_id)
  emails = _paginate(request, email_list)
  
  data = {}
  data["emails"] = emails 
  add_main_menu(data)
  return render_to_response("listEmails.html", data)

def email_detail(request, email_id):
  """
  Display the details of a single email identified by email_id. If the email
  does not exist then return a 404 error)
  """
  email = get_object_or_404(Message, pk=email_id)
  data = {}
  data["email"] = email
  add_main_menu(data)
  return render_to_response("detailEmail.html", data)

def list_email_tickets(request):
    """
    List all tickets that are related to an email in some way.
    """
    data = {}
    tickets = Ticket.objects.filter(status = Ticket.OPEN_STATUS).order_by('priority', 'modified')
    data["tickets"] = _paginate(request, tickets)
    add_main_menu(data)
    return render_to_response("listTickets.html", data)

msgid_pattern = re.compile(r'<(.*?)>\s*',re.S)

def get_backlink(mail):
    """ 
    try to estimate the backlink in the given email message 
    We are using the info provided by D.J. Bernstein at http://cr.yp.to/immhf/thread.html
    """

    references = []
    
    reference = mail.get('References')
    if reference:
        references = msgid_pattern.findall(reference)

    reply = mail.get('In-Reply-To')
    if reply:
        replies = msgid_pattern.findall(reply)
        if len(replies) > 0: 
            for reply in replies:
                if not reply in references:
                    references.append(reply)

    if len(references) > 0:
        return references[-1]
    else:
        return None
    
def email_retrieve(request):
    """
    Grab all email for the user and import it into the database.
    Currently we only handle pop3 accounts.
    """
    server = poplib.POP3_SSL(settings.SUBSCRIPTION_POP3_SERVER, 995)
    server.getwelcome()
    server.user(settings.SUBSCRIPTION_POP3_USER)
    server.pass_(settings.SUBSCRIPTION_POP3_PASSWORD)

    messagesInfo = server.list()[1]

    for msg in messagesInfo:
        msgNum = msg.split(" ")[0]
        msgSize = msg.split(" ")[1]
        full_message = "\n".join(server.retr(msgNum)[1])

        msg = email.message_from_string(full_message)

        record_email(msg)
        
        if settings.SUBSCRIPTION_POP3_DELETE:
            server.dele(msgNum)
    server.quit()
    
    email_list = Message.objects.all()
    emails = _paginate(request, email_list)
  
    return redirect("list_email_tickets")

  
def record_email(mail):
    """
    Record a single email in the database. Included messageProcessingPlugin
    will be run against the message.
    
    Returns a a boolean indicating if a new email were created and a
    dictionary of all the values relating to this email.
    """
    body = ""
    date = None
    address = None
    pgp = None
    msgId = None
    backlink = None
    
    date_header = mail.get('Date')
    if (date_header): 
        EpochSeconds = time.mktime(email.Utils.parsedate(date_header))
        date = datetime.fromtimestamp(EpochSeconds)
        
    subject = mail.get('Subject', "Blank subject")
    if mail.is_multipart():
        for part in mail.walk():
            type = part.get_content_type()
            if type == 'application/pgp-signature':
                pgp = part.get_payload(decode=False)
            elif type == "text/plain":
                body += part.get_payload(decode=True)
    else:
        body = mail.get_payload(decode=True)
            
    raw = mail.as_string()
        
    msgID_header = mail.get('Message-Id')
    if (msgID_header): 
        msgID = email.Utils.unquote(msgID_header)
            
    backlink_header = get_backlink(mail)
    if (backlink_header): 
        backlink = string.replace(email.Utils.unquote(backlink_header), "\n", "")
    
    address_header = mail.get('From')
    if (address_header): 
        address = email.Utils.parseaddr(address_header)[1].lower()
        try:
          participant = Participant.objects.get(emailAddr=address)
        except Participant.DoesNotExist:
          participant = Participant(emailAddr=address, pgp=pgp)
          participant.save()
  
    replyTo_header = mail.get('Reply-To')
    if not replyTo_header: 
        replyTo_header = address_header
  
    list_header = mail.get('list-id')
    if list_header:
        list_name = list_header
    else:
        list_name = mail.get("To") 
    list, created = Maillist.objects.get_or_create(name=list_name)
    
    values = {'date': date,
              'fromParticipant': participant,
              'replyTo': replyTo_header,
              'backlink': backlink,
              'list': list,
              'subject': unicode(subject, errors='ignore'),
              'body': unicode(body, errors='ignore')}
    mail, created = Message.objects.get_or_create(messageID=msgID, defaults=values)
    
    if created:
        plugins.processPlugins(mail)
                    
    return created, values
