from django.db import models
from django.core.exceptions import ObjectDoesNotExist

# Create your models here.
class Company(models.Model):
    """
    Contains companies users may be assigned to.
    """
    class Meta: # pylint: disable=missing-docstring
        db_table = "company"

    title = models.CharField(blank=True, max_length=255, db_index=True)
    address = models.TextField(blank=True)
    real_address = models.TextField(blank=True)
    inn = models.CharField(blank=True, max_length=255)
    kpk = models.CharField(blank=True, max_length=255)
    ceo_name = models.CharField(blank=True, max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(blank=True, max_length=255)


    def get_representative(self):
        """
        Gets list of student profiles assigned to the company
        """
        representative = None
        try:
            representative = self.userprofile_set.get(is_representative__exact=1, user__is_active=1)
        except ObjectDoesNotExist:
            pass

        return representative