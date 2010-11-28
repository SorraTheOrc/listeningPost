from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.db import models

import re

class Maillist(models.Model):
    name = models.CharField(max_length = 35, primary_key=True)
    
    def _get_email_count(self):
        return EmailMessage.objects.filter(list = self).count()
    email_count = property(_get_email_count)
    
    def __unicode__(self):
        return u"%s" % (self.name)

class Archive(models.Model):
    filename = models.CharField(max_length = 150, primary_key=True)
    list = models.ForeignKey(Maillist)

    def __unicode__(self):
        return u"%s" % (self.filename)

class Participant(models.Model):
    id = models.AutoField(primary_key = True)
    emailAddr = models.CharField(max_length=200, unique=True)
    pgp = models.TextField(null=True)
    
    def increaseMailCount(self):
        self.email_count += 1

    def _getEmailCount(self):
        return EmailMessage.objects.filter(fromParticipant = self).count()
    email_count = property(_getEmailCount)

    def _getReplyToOthersCount(self):
        return EmailMessage.objects.filter(fromParticipant = self).exclude(backlink = None).count()
    reply_to_count = property(_getReplyToOthersCount)

    def _get_label(self):
      at = self.emailAddr.find('@')
      if at:
        label = self.emailAddr[:at]
      else:
        label = self.emailAddr
      return label
    label = property(_get_label)

    def __unicode__(self):
        return u"%s" % (self.emailAddr)

class EmailMessage(models.Model):
    id = models.AutoField(primary_key = True)
    messageID = models.CharField(max_length=200, unique = True)
    date = models.DateTimeField()
    fromParticipant = models.ForeignKey(Participant)
    backlink = models.CharField(max_length=200, null = True)
    list = models.ForeignKey(Maillist)
    subject = models.CharField(max_length=150)
    body = models.TextField()

    def _get_word_dictionary(self):
        """
        Get a dictionary containing a count of words in the body of this email.
        Common stop words and punctioation are removed.
        """
        content = self.body.lower()
        # strip signatures
        sig_start = content.find('___')
        if not sig_start:
            sig_start = content.find('---')
        if sig_start:
            content = content[:sig_start]
        
        punctuation = re.compile(r'[.?!,":;*+<>''-]')
        content = punctuation.sub("", content)
        
        wordlist = content.split()
        stopwords = "a all and are as at be but for from in is it of on so this there to the was with"
        
        freq_dict = {}
        
        for word in wordlist:
            if word not in stopwords:
              try:
                freq_dict[str(word)] += 1
              except:
                freq_dict[str(word)] = 1
        return freq_dict
    dictionary = property(_get_word_dictionary)

    def _get_word_count(self):
        """
        Get a sotrted list containing a count of words in the body of this email.
        Common stop words and punctioation are removed.
        """
        print "in word count"
        freq_dict = self._get_word_dictionary()
        freq_list = freq_dict.items()
        return sorted(freq_list, key = lambda word: -word[1])
    word_count = property(_get_word_count)

    def __unicode__(self):
        return u"'%s' on '%s' from %s" % (self.subject, self.list.name, self.fromParticipant.emailAddr)

    class Meta:
        ordering = ('date',)
                
class EmailAction(models.Model):
    """
    Records an action that needs to be taken on an email object.
    """
    id = models.AutoField(primary_key = True)
    email_message = models.ForeignKey(EmailMessage)
    type = models.IntegerField()
    description = models.TextField()
    complete = models.BooleanField(default = False)
    due = models.DateField()

    def _get_name(self):
        if self.type == 1:
            return "Ensure Reply"
    name = property(_get_name) 
    
    def __unicode__(self):
        return u"%s on '%s'" % (self.name, self.email_message.subject)

    class Meta:
        ordering = ('due',)
    
def message_saved(sender, instance, created, **kwargs):
    if created:
        # if this is in reply to another mail we already have, flag other mail as replied to
        if instance.backlink is not None:
            try:
              repliedTo = EmailMessage.objects.filter(messageID = instance.backlink)[0]
              action = EmailAction.objects.filter(email_message = repliedTo)[0]
              action.complete = True
              action.save()
            except:
              pass
                
        # if this mail doesn't already have a reply then set an action to check for one
        try:
            replies = EmailMessage.objects.filter(backlink = instance.messageID).count()
            if replies == 0:
                due = datetime.now() + timedelta(3)
                EmailAction(email_message = instance, type = 1, due = due, description = "Ensure response given").save()
        except:
              pass
                
post_save.connect(message_saved, sender=EmailMessage)