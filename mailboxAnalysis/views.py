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
        if email.backlink is not None:
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
  return render_to_response('index.html', data, context_instance = RequestContext(request))

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
  
  return render_to_response("report.html", data, context_instance = RequestContext(request))
  
def social_graph(request, participant_id):
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
  return render_to_response("socialGraph.html", data, context_instance = RequestContext(request))

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
  in the projects data_directory, within this folder there should be one
  or more archive files for the mail list.
  data_directory defaults to the project root directory.
  """
  global data_directory

  list_name = request.POST['list']
  input = os.path.join(data_directory, list_name)
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
