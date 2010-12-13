import textwrap

def process(mail):
    """
    Wrap the body of a message to ensure that each line is a maximum of
    72 characters in length.
    """
    body = mail.body
    new_body = ""
    for para in body.split('\n'):
        new_body += "\n"
        new_body += textwrap.fill(para, 72)
    if not new_body == mail.body:
        print "updating body"
        mail.body = new_body
        mail.save()
