from django.db import models

class Menu(models.Model):
    """
    A menu contains a number of menu items. If a base_url is supplied
    the menu item will only be displayed when the current page is
    below that base_url. If no base_url is provided then it will 
    always be displayed.
    """
    name = models.CharField(max_length=20)
    slug = models.SlugField(primary_key=True)
    base_url = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Admin:
        pass

    def __unicode__(self):
        return "%s" % self.name

    def save(self):
        """
        Update the order number of items to make plenty of space between
        them. That is if we have three items with order number 1, 2, and 12
        we will end up with 10, 20, 30. This ensures items can be reordered
        without the need to manually change all values.
        """
        super(Menu, self).save()

        current = 10
        for item in MenuItem.objects.filter(menu=self).order_by('order'):
            item.order = current
            item.save()
            current += 10

class MenuItem(models.Model):
    """
    A single item in a menu. The ordering of items in menus is dependent on the
    order field, with lower values being displayed first. If login_required is
    set to true then the item will only be displayed to logged in users.
    """
    slug = models.SlugField(primary_key=True)
    menu = models.ForeignKey(Menu)
    order = models.IntegerField()
    link_url = models.CharField(max_length=100, help_text='URL or URI to the content, eg /about/ or http://foo.com/')
    title = models.CharField(max_length=100)
    login_required = models.BooleanField(default=False)

    class Admin:
        pass

    def __unicode__(self):
        return "%s %s. %s" % (self.menu.slug, self.order, self.title)
