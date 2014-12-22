
from datetime import datetime
import json
from pytz import UTC

from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils.translation import ugettext_noop
from django_countries.fields import CountryField

# Create your models here.
class UserProfile(models.Model):
    """This is where we store all the user demographic fields. We have a
    separate table for this rather than extending the built-in Django auth_user.

    Notes:
        * Some fields are legacy ones from the first run of 6.002, from which
          we imported many users.
        * Fields like name and address are intentionally open ended, to account
          for international variations. An unfortunate side-effect is that we
          cannot efficiently sort on last names for instance.

    Replication:
        * Only the Portal servers should ever modify this information.
        * All fields are replicated into relevant Course databases

    Some of the fields are legacy ones that were captured during the initial
    MITx fall prototype.
    """

    class Meta:  # pylint: disable=missing-docstring
        db_table = "auth_userprofile"

    # CRITICAL TODO/SECURITY
    # Sanitize all fields.
    # This is not visible to other users, but could introduce holes later
    user = models.OneToOneField(User, unique=True, db_index=True, related_name='profile')
    name = models.CharField(blank=True, max_length=255, db_index=True)

    meta = models.TextField(blank=True)  # JSON dictionary for future expansion
    courseware = models.CharField(blank=True, max_length=255, default='course.xml')

    # Location is no longer used, but is held here for backwards compatibility
    # for users imported from our first class.
    language = models.CharField(blank=True, max_length=255, db_index=True)
    location = models.CharField(blank=True, max_length=255, db_index=True)

    # Optional demographic data we started capturing from Fall 2012
    this_year = datetime.now(UTC).year
    VALID_YEARS = range(this_year, this_year - 120, -1)
    year_of_birth = models.IntegerField(blank=True, null=True, db_index=True)
    GENDER_CHOICES = (
        ('m', ugettext_noop('Male')),
        ('f', ugettext_noop('Female')),
        # Translators: 'Other' refers to the student's gender
        ('o', ugettext_noop('Other'))
    )
    gender = models.CharField(
        blank=True, null=True, max_length=6, db_index=True, choices=GENDER_CHOICES
    )

    # [03/21/2013] removed these, but leaving comment since there'll still be
    # p_se and p_oth in the existing data in db.
    # ('p_se', 'Doctorate in science or engineering'),
    # ('p_oth', 'Doctorate in another field'),
    LEVEL_OF_EDUCATION_CHOICES = (
        ('p', ugettext_noop('Doctorate')),
        ('m', ugettext_noop("Master's or professional degree")),
        ('b', ugettext_noop("Bachelor's degree")),
        ('a', ugettext_noop("Associate's degree")),
        ('hs', ugettext_noop("Secondary/high school")),
        ('jhs', ugettext_noop("Junior secondary/junior high/middle school")),
        ('el', ugettext_noop("Elementary/primary school")),
        # Translators: 'None' refers to the student's level of education
        ('none', ugettext_noop("None")),
        # Translators: 'Other' refers to the student's level of education
        ('other', ugettext_noop("Other"))
    )
    level_of_education = models.CharField(
        blank=True, null=True, max_length=6, db_index=True,
        choices=LEVEL_OF_EDUCATION_CHOICES
    )
    mailing_address = models.TextField(blank=True, null=True)
    city = models.TextField(blank=True, null=True)
    country = CountryField(blank=True, null=True)
    goals = models.TextField(blank=True, null=True)
    allow_certificate = models.BooleanField(default=1)

    # Unital-specific fields
    phone = models.TextField(blank=True, null=True)
    is_representative = models.BooleanField(default=0)
    # company = models.ForeignKey(Company, db_index=True, blank=True, null=True)

    def get_meta(self):  # pylint: disable=missing-docstring
        js_str = self.meta
        if not js_str:
            js_str = dict()
        else:
            js_str = json.loads(self.meta)

        return js_str

    def set_meta(self, meta_json):  # pylint: disable=missing-docstring
        self.meta = json.dumps(meta_json)

    def set_login_session(self, session_id=None):
        """
        Sets the current session id for the logged-in user.
        If session_id doesn't match the existing session,
        deletes the old session object.
        """
        meta = self.get_meta()
        meta['session_id'] = session_id
        self.set_meta(meta)
        self.save()

    @transaction.commit_on_success
    def update_name(self, new_name):
        """Update the user's name, storing the old name in the history.

        Implicitly saves the model.
        If the new name is not the same as the old name, do nothing.

        Arguments:
            new_name (unicode): The new full name for the user.

        Returns:
            None

        """
        if self.name == new_name:
            return

        if self.name:
            meta = self.get_meta()
            if 'old_names' not in meta:
                meta['old_names'] = []
            meta['old_names'].append([self.name, u"", datetime.now(UTC).isoformat()])
            self.set_meta(meta)

        self.name = new_name
        self.save()

    @transaction.commit_on_success
    def update_email(self, new_email):
        """Update the user's email and save the change in the history.

        Implicitly saves the model.
        If the new email is the same as the old email, do not update the history.

        Arguments:
            new_email (unicode): The new email for the user.

        Returns:
            None
        """
        if self.user.email == new_email:
            return

        meta = self.get_meta()
        if 'old_emails' not in meta:
            meta['old_emails'] = []
        meta['old_emails'].append([self.user.email, datetime.now(UTC).isoformat()])
        self.set_meta(meta)
        self.save()

        self.user.email = new_email
        self.user.save()