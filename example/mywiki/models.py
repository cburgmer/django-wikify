from django.db import models
import reversion

class Page(models.Model):
    """Simple Wiki page model"""
    title = models.CharField(max_length=255, primary_key=True)
    content = models.TextField(blank=True)

    def __unicode__(self):
        return self.title

reversion.register(Page)
