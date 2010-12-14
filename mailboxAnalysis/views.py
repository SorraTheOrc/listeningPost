from mailboxAnalysis.models import Archive
from mailboxAnalysis.models import Message
from mailboxAnalysis.models import Maillist
from mailboxAnalysis.models import Participant
from datetime import datetime, timedelta
from decimal import *
from django.conf import settings
from django.core.context_processors import csrf
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.http import HttpResponse
from django.shortcuts import redirect, render_to_response, get_object_or_404
from django.template import RequestContext
from helpdesk.models import FollowUp, Queue, Ticket
import os, email.Utils, glob, gzip, mailbox, poplib, operator, re, string, time

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

def _get_social_graph(emails, participant, decay = 5, maxage = 2000, depth = 2):
    """
    Given a set of emails from a participant calculate the social graph contained within them.
    An email that is a reply to another implies a relationship between the two aprticipants.
    An email in reply to one of the supplied emails also implies a relationship.
    The strength of the relationship is strong the more recently the exchange took place.
    Higher 'decay' values result in weaker relationships over time. 
    Emails exchanged over 'maxage' days ago are not counted.
    """
    friends = {}
    earliest_date = datetime.now() - timedelta(maxage)
    for email in emails:
        if email.backlink is not None and not email.fromParticipant == participant:
            replyTo = Message.objects.filter(messageID=email.backlink).filter(date__gte=earliest_date)
            if len(replyTo) == 1:
                repliedParticipant = replyTo[0].fromParticipant
                try:
                    strength = friends[str(repliedParticipant.emailAddr)]
                except:
                    strength = 0
                
                daysOld = (datetime.now() - email.date).days
                friends[str(repliedParticipant.emailAddr)] = strength + ((maxage - daysOld) / decay)
                                
            elif len(replyTo) > 1:
                raise NotSupportException("We can't currently handle multiple emails with the same message ID")
            
        replies = Message.objects.filter(backlink=email.messageID).filter(date__gte=earliest_date)
        for reply in replies:
            if not reply.fromParticipant == participant:
                friend = reply.fromParticipant
                try:
                    strength = friends[str(friend.emailAddr)]
                except:
                    strength = 0
                daysOld = (datetime.now() - reply.date).days
                friends[str(friend.emailAddr)] = strength + ((maxage - daysOld) / decay)
            
    friends = sorted(friends.iteritems(), key=operator.itemgetter(1))
    friends.reverse()
    return friends

data_directory = "archives"

def index(request):
  data = {}
  data["total_lists"] = Maillist.objects.count()
  data["total_emails"] = Message.objects.count()
  data["total_participants"] = Participant.objects.count()
  add_main_menu(data)
  return render_to_response('index.html', data)

def list_participants(request):
  participants = _paginate(request, Participant.objects.all())
  data = {}
  data["participants"] = participants
  add_main_menu(data)
  return render_to_response("listParticipants.html", data)

def participant_detail(reqeust, participant_id):
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
  
  add_main_menu(data)
  return render_to_response("detailParticipant.html", data)

def participant_emails(request, participant_id):
  emails = _paginate(request, Message.objects.filter(fromParticipant = participant_id))
  data = {}
  data["emails"] = emails
  add_main_menu(data)
  return render_to_response("listEmails.html", data)
  
def report(request):
  earliest_date = datetime.now() - timedelta(30)
  data = {}
  data["total_participants"] = Participant.objects.count()
  data["total_emails"] = Message.objects.all().count()
  
  new_participants = []
  participants = Participant.objects.all().distinct()
  for participant in participants:
    emails = Message.objects.filter(fromParticipant = participant).order_by("date")[0:1]
    for email in emails:
        if email.date >= earliest_date:
            new_participants.append(participant)
  data["new_participants"] = new_participants
  
  reply_queue = Queue.objects.get(pk=1)
  data["reply_actions"] = Ticket.objects.filter(queue = reply_queue).filter(status = Ticket.OPEN_STATUS)
  
  data["other_open_actions"] = Ticket.objects.exclude(queue = reply_queue).filter(status = Ticket.OPEN_STATUS)
  
  add_main_menu(data)
  return render_to_response("report.html", data)
  
def participant_social(request, participant_id):
  """
  Calculate and display the social graph for a given participant.
  """
  data = {}

  participant = get_object_or_404(Participant, pk=participant_id)
  data["participant"] = participant

  emails = Message.objects.filter(fromParticipant = participant)

  friends = _get_social_graph(emails, participant)

  # Create DOT file
  dot = ""
  if len(friends) > 0:
      min_weight = friends[len(friends)-1][1]
      max_weight = friends[0][1]
    
      dot = "graph G {\n"
      dot += "model=circuit;\n"
      dot += '"' + str(participant.emailAddr) + '" [color=red, style=filled, fillcolor=red, fontcolor=yellow, label="' + participant.label + '"];\n\n'
      for friend, strength in friends:
        at = friend.find('@')
        if at:
          label = friend[:at]
        else:
          label = friend
        dot += '"' + str(participant) + '" -- "' + friend + '" [len = ' + str(2 + (Decimal(min_weight - strength) / Decimal(max_weight))) + '];\n'
        dot += '"' + friend + '" [color=black, fontcolor=black, label="' + label  + '"];\n'
        
        dot += '\n'
      dot += "\n}"

  data["participants"] = friends
  data["dot"] = dot
  add_main_menu(data)
  return render_to_response("socialGraph.html", data)

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
  
  results = crawl(input)
  results["list"] = list_name
  emails_after = Message.objects.count()
  results["total_emails"] = emails_after
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


def crawl(input):
  """
  Crawl a directory that should contain mail archives and process any archives found
  that have not yet been processed.
  """
  global data_directory
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
      
  archive = Archive(file, list)
  archive.save()

  return {"processed": processed, "created": new, "duplicate": duplicate, 
          "invalid": invalid, "with_backlink": processed - no_backlink, 
          "no_backlink": no_backlink}

def add_main_menu(data):
    """
    Add the main menu items to the data dictionary.
    """
    data["menu"] = [{"text": "Home", "href":  "/analysis"},
                    {"text": "Inbox", "href":  "/mail/inbox"},
                    {"text": "Mail Lists", "href":  "/mail/mailinglist/list"},
                    {"text": "List participants", "href":  "/analysis/participant/list"},
                    {"text": "Import archives", "href":  "/analysis/configureImport"},
                    {"text": "Actions", "href":  "/mail/ticket/list"},
                    {"text": "Retrieve", "href":  "/mail/retrieve"},
                    {"text": "Report", "href":  "/analysis/report"},]
    return data
