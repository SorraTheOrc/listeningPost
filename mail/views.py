from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.shortcuts import redirect, render_to_response, get_object_or_404

from mailboxAnalysis.views import add_main_menu
from mailboxAnalysis.models import Message

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
    
def email_inbox(request, list_id = None):
  """
  Create a list of all emails in an inbox. An inbox is either all mail for a 
  user (default) or all email in a list (when list_id is provived)
  """
  if list_id is None:
      email_list = Message.objects.all()
  else:
      email_list = Message.objects.filter(list = list_id)
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
  email = get_object_or_404(Message, pk = email_id)
  data = {}
  data["email"] = email
  add_main_menu(data)
  return render_to_response("detailEmail.html", data)
