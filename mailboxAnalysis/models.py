from datetime import datetime, timedelta
from django.db.models.signals import post_save
from django.db import models
from helpdesk.models import Ticket

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
        stopwords = "a able about above according accordingly across actually after afterwards again against ain't all allow allows almost alone along already also although always am among amongst an and another any anybody anyhow anyone anything anyway anyways anywhere apart appear appreciate appropriate are aren't around as aside ask asking associated at available away awfully be became because become becomes becoming been before beforehand behind being believe below beside besides best better between beyond both brief but by c'mon c's came can can't cannot cant cause causes certain certainly changes clearly co com come comes concerning consequently consider considering contain containing contains corresponding could couldn't course currently definitely described despite did didn't different do does doesn't doing don't done down downwards during each edu eg eight either else elsewhere enough entirely especially et etc even ever every everybody everyone everything everywhere ex exactly example except far few fifth first five followed following follows for former formerly forth four from further furthermore get gets getting given gives go goes going gone got gotten greetings had hadn't happens hardly has hasn't have haven't having he he's hello help hence her here here's hereafter hereby herein hereupon hers herself hi him himself his hither hopefully how howbeit however i'd i'll i'm i've ie if ignored immediate in inasmuch inc indeed indicate indicated indicates inner insofar instead into inward is isn't it it'd it'll it's its itself just keep keeps kept know knows known last lately later latter latterly least less lest let let's like liked likely little look looking looks ltd mainly many may maybe me mean meanwhile merely might more moreover most mostly much must my myself name namely nd near nearly necessary need needs neither never nevertheless new next nine no nobody non none noone nor normally not nothing novel now nowhere obviously of off often oh ok okay old on once one ones only onto or other others otherwise ought our ours ourselves out outside over overall own particular particularly per perhaps placed please plus possible presumably probably provides que quite qv rather rd re really reasonably regarding regardless regards relatively respectively right said same saw say saying says second secondly see seeing seem seemed seeming seems seen self selves sensible sent serious seriously seven several shall she should shouldn't since six so some somebody somehow someone something sometime sometimes somewhat somewhere soon sorry specified specify specifying still sub such sup sure t's take taken tell tends th than thank thanks thanx that that's thats the their theirs them themselves then thence there there's thereafter thereby therefore therein theres thereupon these they they'd they'll they're they've think third this thorough thoroughly those though three through throughout thru thus to together too took toward towards tried tries truly try trying twice two un under unfortunately unless unlikely until unto up upon us use used useful uses using usually value various very via viz vs want wants was wasn't way we we'd we'll we're we've welcome well went were weren't what what's whatever when whence whenever where where's whereafter whereas whereby wherein whereupon wherever whether which while whither who who's whoever whole whom whose why will willing wish with within without won't wonder would would wouldn't yes yet you you'd you'll you're you've your yours yourself yourselves zero"
        
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
                