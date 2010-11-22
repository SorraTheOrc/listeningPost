from mailboxAnalysis.models import Archive
from mailboxAnalysis.models import EmailMessage
from mailboxAnalysis.models import Maillist
from mailboxAnalysis.models import Participant
from django.core.context_processors import csrf
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
import os, datetime, email.Utils, glob, gzip, mailbox, re, string, time

data_directory = "archives"

def index(request):
  data = {}
  data["total_lists"] = Maillist.objects.count()
  data["total_emails"] = EmailMessage.objects.count()
  data["total_participants"] = Participant.objects.count()
  add_main_menu(data)
  return render_to_response('index.html', data)

def list_participants(reqeust):
  data = {}
  data["participants"] = Participant.objects.all()
  add_main_menu(data)
  return render_to_response("listParticipants.html", data)

def participant_detail(reqeust, participant_id):
  data = {}
  data["participant"] = get_object_or_404(Participant, pk=participant_id)
  add_main_menu(data)
  return render_to_response("detailParticipant.html", data)

def participant_emails(reqeust, participant_id):
  data = {}
  data["emails"] = EmailMessage.objects.filter(fromParticipant = participant_id)
  add_main_menu(data)
  return render_to_response("listEmails.html", data)

def email_detail(request, email_id):
  data = {}
  data["email"] = get_object_or_404(EmailMessage, pk=email_id)
  add_main_menu(data)
  return render_to_response("detailEmail.html", data)

def email_inbox(request):
  data = {}
  data["emails"] = EmailMessage.objects.all()
  add_main_menu(data)
  return render_to_response("listEmails.html", data)

def configure_import(request):
  """
  Render a form which allows the user to configure an analysis run
  that will import any new messages.
  """
  data = {}
  data.update(csrf(request))
  add_main_menu(data)
  
  return render_to_response('configureImport.html', 
                            data,
                            context_instance = RequestContext(request))

def start_import(request):
  """
  Start a request from a POST. The request variable 'list' should contain
  the name of the list we want to process. This name should be a directory
  in the projects data_directory, within this folder there should be one
  or more archive files for the mail list.
  data_directory defaults to the project root directory.
  """
  global data_directory

  emails_before = EmailMessage.objects.count()

  list_name = request.POST['list']
  input = os.path.join(data_directory, list_name)
  if (not os.path.exists(input)):
      return render_to_response('configureAnalysis.html',
                                {'error_message': "Unable to find any archives for the list '" + list_name + "' (looked in " + os.path.abspath(input) + ")"},
                                context_instance=RequestContext(request))

  if (not os.path.isdir(input)):
      return render_to_response('configureAnalysis.html',
                                {'error_message': input + " exits but is not a directory"},
                                context_instance=RequestContext(request))
  
  results = crawl(input, list_name)
  results["list"] = list_name
  emails_after = EmailMessage.objects.count()
  results["total_emails"] = emails_after
  results["imported"] = emails_after - emails_before
  add_main_menu(results)

  return render_to_response("importResults.html",
                            results,
                            context_instance = RequestContext(request))

def msgfactory(file):
    """ create a mail message from the given file """
    
    try:
        return email.message_from_file(file)
    except:
        return ''


def crawl(input, list_name):
  """
  Crawl a directory that should contain mail archives and process any archives found
  that have not yet been processed.
  """
  global data_directory
  results = None

  files = glob.glob(input + "/*")
  files.sort()
  for f in files:
      results = process(f, list_name)
  return results
    
msgid_pattern = re.compile(r'<(.*?)>\s*',re.S)

def get_backlink(mail):
    """ 
    try to estimate the backlink in the given email message 
    We are using the info provided by D.J. Bernstein at http://cr.yp.to/immhf/thread.html
    """

    # start with an empty list of references
    references = []
    
    # first, get all the references to anything that looks like a message ID
    reference = mail.get('References')
    if reference:
        references = msgid_pattern.findall(reference)

    # second, if we have an reply-to header, get the message ID out of it and 
    # append it to the references, in case it's not there yet.
    reply = mail.get('In-Reply-To')
    if reply:
        replies = msgid_pattern.findall(reply)
        if len(replies) > 0: 
            for reply in replies:
                if not reply in references:
                    references.append(reply)

    # finally, return the last one of the references, which should be the
    # most immediate parent.
    
    if len(references) > 0:
        return references[-1]
    else:
        return ""
    

def process(file, list_name):
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

  for mail in mbox:
      body = ""
      date = None
      address = None
      pgp = None
      msgId = None
      backlink = None
      
      if (mail != ''):
            processed += 1
            date_header = mail.get('Date')
            if (date_header): 
                EpochSeconds = time.mktime(email.Utils.parsedate(date_header))
                date = datetime.datetime.fromtimestamp(EpochSeconds)
                
            subject = mail.get('Subject', "Blank subject")
            if mail.is_multipart():
                for part in mail.walk():
                    type =  part.get_content_type()
                    if type == 'application/pgp-signature':
                        pgp = part.get_payload(decode=False)
                    elif type == "text/plain":
                        body += part.get_payload(decode=False)
            else:
                body =  mail.get_payload(decode=False)
            
            raw = mail.as_string()
                
            msgID_header = mail.get('Message-Id')
            if (msgID_header): 
                msgID = email.Utils.unquote(msgID_header)
                
            backlink_header = get_backlink(mail)
            if (backlink_header): 
                backlink = string.replace(email.Utils.unquote(backlink_header),"\n","")
            else:
                no_backlink += 1

            address_header = mail.get('From')
            if (address_header): 
                address = email.Utils.parseaddr(address_header)[1].lower()
                try:
                  participant = Participant.objects.get(emailAddr = address)
                except Participant.DoesNotExist:
                  participant = Participant(emailAddr = address, pgp = pgp)
                  participant.save()
          
            list = Maillist(list_name)
            list.save()

            mail = EmailMessage(messageID = msgID, 
                                date = date, 
                                fromParticipant = participant,
                                backlink = backlink, 
                                list = list, 
                                subject = subject, 
                                body = body)
            mail.save()
            print "Processed mail from " + mail.fromParticipant.emailAddr + " on", mail.date
      else:
          invalid += 1
          print "Invalid mail"

  archive = Archive(file, list)
  archive.save()

  return {"processed": processed, "invalid": invalid, "with_backlink": processed - no_backlink, "no_backlink": no_backlink}

def add_main_menu(data):
    """
    Add the main menu items to the data dictionary.
    """
    data["menu"] = [{"text": "Home", "href":  "/analysis"},
                    {"text": "Inbox", "href":  "/analysis/mail/inbox"},
                    {"text": "List participants", "href":  "/analysis/participant/list"},
                    {"text": "Import archives", "href":  "/analysis/configureImport"},]
    return data
