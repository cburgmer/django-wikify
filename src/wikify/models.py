from django.db import models

class VersionMeta(models.Model):
    """ Additional meta data for revisions. """
    revision = models.ForeignKey("reversion.Revision")
    ip_address = models.IPAddressField()
