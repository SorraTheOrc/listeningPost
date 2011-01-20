import email.Utils, glob, gzip, mailbox, os, poplib, re, string, time

from datetime import datetime, timedelta

from django.conf import settings
from django.core.context_processors import csrf
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext  

from helpdesk.models import FollowUp, Queue, Ticket

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
  return render_to_response("listEmails.html", data, context_instance = RequestContext(request))

def email_detail(request, email_id):
  """
  Display the details of a single email identified by email_id. If the email
  does not exist then return a 404 error)
  """
  email = get_object_or_404(Message, pk=email_id)
  data = {}
  data["email"] = email
  return render_to_response("detailEmail.html", data, context_instance = RequestContext(request))

def list_email_tickets(request):
    """
    List all tickets that are related to an email in some way.
    """
    data = {}
    tickets = Ticket.objects.filter(status = Ticket.OPEN_STATUS).order_by('priority', 'modified')
    data["tickets"] = _paginate(request, tickets)
    return render_to_response("listTickets.html", data, context_instance = RequestContext(request))

def ticket_mark_complete(request, ticket_id):
  resolution = "Marked complete by " + request.user.username
  action = Ticket.objects.get(pk=ticket_id)
  follow_up = FollowUp (
                        ticket=action,
                        date=datetime.now(),
                        comment=resolution,
                        title="Reply Sent",
                        public=True)
  follow_up.save()
  
  action = get_object_or_404(Ticket, pk=ticket_id)
  action.status = Ticket.CLOSED_STATUS
  action.resolution = follow_up.comment
  action.save()
  
  return redirect("list_email_tickets")

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
    
def email_send(request):
  """
  Send an email. The post request should contain the necessary data for
  sending the mail as follows:
  subject: the subject of the email
  body: the body of the email
  to: the to address
  """
  body = request.POST['body']
  to = request.POST['to']
  subject = request.POST['subject']
  reply_to_id = request.POST['reply_to_id']
  message_id = email.utils.make_msgid()
  
  mail = EmailMessage(subject, body, 'from@example.com',
                      [to],
                      headers = {'Message-ID': message_id, 'In-Reply-To': reply_to_id})
  mail.send()

  queue = Queue.objects.get(pk=1)
  if reply_to_id:
      replyTo = Message.objects.get(id = reply_to_id)
      actions = replyTo.action.filter(queue=queue)
      resolution = 'Reply sent on %s' % (datetime.now())
      for action in actions:
          follow_up = FollowUp (
                                ticket=action,
                                date=datetime.now(),
                                comment=resolution,
                                title="Reply sent",
                                public=False)
          follow_up.save()
            
          action.status = Ticket.RESOLVED_STATUS
          action.resolution = follow_up.comment
          action.save()
  
  return redirect("list_email_tickets")

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

def email_compose(request):
  data = {}
  data.update(csrf(request))
  return render_to_response("composeEmail.html", data, context_instance = RequestContext(request))

def email_reply(request, email_id):
  email = get_object_or_404(Message, pk = email_id)
  data = {}
  data.update(csrf(request))
  data["to"] = email.replyTo
  data["reply_to_id"] = email.id
  
  subject = email.subject
  if not subject.startswith('Re:'):
    subject = "Re: " + subject
  data["subject"] = subject
  
  body = "On "
  body += email.date.strftime("%d/%m/%y")
  body += " "
  body += email.fromParticipant.emailAddr
  body += " said:\n"  
  
  for line in email.body.splitlines():
    if line.startswith('>'):
        body += ">" + line + "\n"
    else:
        body += "> " + line + "\n"
  data["body"] = body
  return render_to_response("composeEmail.html", data, context_instance = RequestContext(request))
  
def mailinglist_list(request):
    """
    Provide a list of all the mailing lists we are aware of.
    """
    lists = _paginate(request, Maillist.objects.all())
    data = {}
    data["lists"] = lists
    return render_to_response("listMailinglist.html", data, context_instance = RequestContext(request))
  
def list_participants(request):
  participants = _paginate(request, Participant.objects.all())
  data = {}
  data["participants"] = participants
  return render_to_response("listParticipants.html", data, context_instance = RequestContext(request))

def participant_emails(request, participant_id):
  emails = _paginate(request, Message.objects.filter(fromParticipant = participant_id))
  data = {}
  data["emails"] = emails
  return render_to_response("listEmails.html", data, context_instance = RequestContext(request))

def participant_detail(request, participant_id):
  data = {}
  participant = get_object_or_404(Participant, pk=participant_id)
  data["participant"] = participant
  data['firstEmail'] = Message.objects.filter(fromParticipant = participant).order_by('date')[0]
  data['lastEmail'] = Message.objects.filter(fromParticipant = participant).order_by('-date')[0]
  
  emails = Message.objects.filter(fromParticipant = participant)
  dictionary = {} 
  for email in emails:
    words = email.dictionary
    for word in words:
      try:
        dictionary[str(word)] += 1
      except:
        dictionary[str(word)] = 1
  data["word_count"] = sorted(dictionary.items(), key = lambda word: -word[1])
  
  return render_to_response("detailParticipant.html", data, context_instance = RequestContext(request))

def configure_import(request):
  """
  Render a form which allows the user to configure an analysis run
  that will import any new messages.
  """
  data = {}
  data.update(csrf(request))
  return render_to_response('configureImport.html', 
                            data,
                            context_instance = RequestContext(request))

def start_import(request):
  """
  Start a request from a POST. The request variable 'list' should contain
  the name of the list we want to process. This name should be a directory
  in the projects DATA_DIRECTORY within this folder there should be one
  or more archive files for the mail list.
  DATA_DIRECTORY defaults to the project root directory.
  """
  list_name = request.POST['list']
  input = os.path.join(settings.DATA_DIRECTORY, list_name)
  if (not os.path.exists(input)):
      return render_to_response('configureImport.html',
                                {'error_message': "Unable to find any archives for the list '" + list_name + "' (looked in " + os.path.abspath(input) + ")"},
                                context_instance=RequestContext(request))

  if (not os.path.isdir(input)):
      return render_to_response('configureImport.html',
                                {'error_message': input + " exits but is not a directory"},
                                context_instance=RequestContext(request))
  
  results = crawl(input)
  results["list"] = list_name
  emails_after = Message.objects.count()
  results["total_emails"] = emails_after
  return render_to_response("importResults.html",
                            results,
                            context_instance = RequestContext(request))

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

def msgfactory(file):
    """ create a mail message from the given file """
    
    try:
        return email.message_from_file(file)
    except:
        return ''

def crawl(input):
  """
  Crawl a directory that should contain mail archives and process any archives found
  that have not yet been processed.
  """
  results = None

  files = glob.glob(input + "/*")
  files.sort()
  for f in files:
      results = process(f)
  return results
    
def process(file):
  """
  Process a single archive file. The archive may, or may not be a gzipped file.
  """
  print "Processing file at " + file
  processed = 0
  invalid = 0
  no_backlink = 0

  if file[-3:] == '.gz':
      input = gzip.open(file, 'r')
  else:
      input = open(file, 'r')

  mbox = mailbox.UnixMailbox(input, msgfactory)

  duplicate = 0
  new = 0

  for mail in mbox:
      if (mail != ''):
          processed += 1
          created, values = record_email(mail)
          if not values["backlink"]: 
              no_backlink += 1
          if created:
              new += 1
          else:
              duplicate += 1
      else:
          invalid += 1
          print "Invalid mail"

  return {"processed": processed, "created": new, "duplicate": duplicate, 
          "invalid": invalid, "with_backlink": processed - no_backlink, 
          "no_backlink": no_backlink}
