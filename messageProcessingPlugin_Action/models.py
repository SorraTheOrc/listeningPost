from django.db import models
from django.utils.translation import ugettext_lazy as _, ugettext
from helpdesk.models import FollowUp, Queue, Ticket

class ActionPattern(models.Model):
    """
    An Action Pattern provides a pattern for a Message. When a Message
    is retrieved with this pattern an given action is created for the
    Message/
    """
    id = models.AutoField(primary_key = True)
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

