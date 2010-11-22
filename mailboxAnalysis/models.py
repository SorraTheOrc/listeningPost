from django.db.models.signals import post_save
from django.db import models

class Maillist(models.Model):
    name = models.CharField(max_length = 35, primary_key=True)

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
    email_count = models.IntegerField(default = 0)
    reply_to_count = models.IntegerField(default = 0)
    
    def increaseMailCount(self):
        self.email_count += 1

    def increaseReplyToCount(self):
        self.reply_to_count += 1

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

    def __unicode__(self):
        return u"'%s' on '%s' from %s" % (self.subject, self.list.name, self.fromParticipant.emailAddr)

    class Meta:
        ordering = ('date',)

def message_saved(sender, instance, created, **kwargs):
    if created:
        fromParticipant = instance.fromParticipant
        fromParticipant.increaseMailCount()
        if instance.backlink is not None:
            fromParticipant.increaseReplyToCount()
        fromParticipant.save()

post_save.connect(message_saved, sender=EmailMessage)
