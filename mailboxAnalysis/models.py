from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext
from helpdesk.models import FollowUp, Queue, Ticket

import re

class Maillist(models.Model):
    name = models.CharField(max_length = 35, primary_key=True)
    
    def _get_email_count(self):
        return Message.objects.filter(list = self).count()
    email_count = property(_get_email_count)
    
    def __unicode__(self):
        return u"%s" % (self.name)

class Archive(models.Model):
    filename = models.CharField(max_length = 150, primary_key=True)
    list = models.ForeignKey(Maillist)

    def __unicode__(self):
        return u"%s" % (self.filename)

class ActionPattern(models.Model):
    """
    An Action Pattern provides a pattern for a Message. When a Message
    is retrieved with this pattern an given action is created for the
    Message/
    """
    subject_pattern = models.CharField(_('Subject pattern'),
                                       max_length=120,
                                       blank = True,
                                       help_text = _('A regular expression to match the subject of a message'),
                                       )
    from_pattern = models.CharField(_('From pattern'),
                                    max_length=120,
                                    blank = True,
                                    help_text = _('A regular expression to match the from address of a message'),
                                    )
    body_pattern = models.CharField(_('Body pattern'),
                                    max_length=240,
                                    blank = True,
                                    help_text = _('A regular expression to match the body of a message'),
                                    )
    action_title = models.CharField(_('Action title'),
                                    max_length=120,
                                    blank = False,
                                    help_text = _('The title of the action'),
                                    )
    action_description = models.TextField(_('Action description'),
                                          blank = False,
                                          help_text = _('The description of the action'),
                                          ) 
    action_priority = models.IntegerField(_('Action priority'),
                                          default = 3,
                                          help_text = _('Priority of the action to be created.')
                                          )
    action_queue = models.ForeignKey('helpdesk.Queue',
                                    help_text = _('The queue that a task should be applied to'),
                                    )
    active = models.BooleanField(
                                 _('Active'),
                                 default = True
                                 )

    def __unicode__(self):
        return u"%s" % (self.subject_pattern)

class Participant(models.Model):
    id = models.AutoField(primary_key = True)
    emailAddr = models.CharField(max_length=200, unique=True)
    pgp = models.TextField(null=True)
    
    def increaseMailCount(self):
        self.email_count += 1

    def _getEmailCount(self):
        return Message.objects.filter(fromParticipant = self).count()
    email_count = property(_getEmailCount)

    def _getReplyToOthersCount(self):
        return Message.objects.filter(fromParticipant = self).exclude(backlink = None).count()
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

class Message(models.Model):
    id = models.AutoField(primary_key = True)
    messageID = models.CharField(max_length=200, unique = True)
    date = models.DateTimeField()
    fromParticipant = models.ForeignKey(Participant)
    backlink = models.CharField(max_length=200, null = True)
    list = models.ForeignKey(Maillist)
    subject = models.CharField(max_length=150)
    body = models.TextField()
    action = models.ManyToManyField(Ticket, related_name="actions")

    def _get_word_dictionary(self):
        """
        Get a dictionary containing a count of words in the body of this email.
        Common stop words and punctuation are removed.
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
    
    def record_reply_received(self, email):
        """
        Record a reply to this mail as a FollowUp to the Reply
        action.
        """
        queue = Queue.objects.get(pk=1)
        actions = self.action.filter(queue=queue)
        resolution = 'Reply received from %s on %s' % (email.fromParticipant, email.date)
        for action in actions:
            follow_up = FollowUp (
                                  ticket=action,
                                  date=datetime.now(),
                                  comment=resolution,
                                  title="Reply received",
                                  public=True)
            follow_up.save()
            
            action.status = Ticket.CLOSED_STATUS
            action.resolution = follow_up.comment
            action.save()
       
    def __unicode__(self):
        return u"'%s' on '%s' from %s" % (self.subject, self.list.name, self.fromParticipant.emailAddr)

    class Meta:
        ordering = ('-date',)
                