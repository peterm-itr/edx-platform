"""
Helper methods related to EdxNotes.
"""
import json
import requests
import logging
from uuid import uuid4
from json import JSONEncoder
from datetime import datetime
from courseware.access import has_access
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.exceptions import ItemNotFoundError
from util.date_utils import get_default_time_display
from dateutil.parser import parse as dateutil_parse
from provider.oauth2.models import AccessToken, Client
from provider.utils import now
from .exceptions import EdxNotesParseError
log = logging.getLogger(__name__)


class NoteJSONEncoder(JSONEncoder):
    """
    Custom JSON encoder that encode datetime objects to appropriate time strings.
    """
    # pylint: disable=method-hidden
    def default(self, obj):
        if isinstance(obj, datetime):
            return get_default_time_display(obj)
        return json.JSONEncoder.default(self, obj)


def get_token(user):
    """
    Generates OAuth access token for a user.
    """
    try:
        token = AccessToken.objects.get(
            client=Client.objects.get(name="edx-notes"),
            user=user,
            expires__gt=now()
        )
    except AccessToken.DoesNotExist:
        token = AccessToken(client=Client.objects.get(name="edx-notes"), user=user)
        token.save()
    return token.token


def send_request(user, course_id, path="", query_string=""):
    """
    Sends a request with appropriate parameters and headers.
    """
    url = get_endpoint(path)
    params = {
        "user": user.username,
        "course_id": unicode(course_id).encode("utf-8"),
    }

    if query_string:
        params.update({
            "text": query_string,
        })

    response = requests.get(
        url,
        headers={
            "x-annotator-auth-token": get_token(user)
        },
        params=params
    )

    return response


def preprocess_collection(user, course, collection):
    """
    Reprocess provided `collection(list)`: adds information about ancestor,
    converts "updated" date, sorts the collection in descending order.

    Raises:
        ItemNotFoundError - when appropriate module is not found.
    """
    store = modulestore()
    filtered_collection = list()
    with store.bulk_operations(course.id):
        for model in collection:
            usage_key = course.id.make_usage_key_from_deprecated_string(model["usage_id"])
            try:
                item = store.get_item(usage_key)
            except ItemNotFoundError:
                log.warning("Module not found: %s", usage_key)
                continue

            if not has_access(user, "load", item, course_key=course.id):
                continue

            model.update({
                u"unit": get_ancestor_context(course, store, usage_key),
                u"updated": dateutil_parse(model["updated"]),
            })
            filtered_collection.append(model)

    sorted_collection = sorted(filtered_collection, key=lambda note: note["updated"], reverse=True)
    return sorted_collection


def search(user, course, query_string):
    """
    Returns search results for the `query_string(str)`.
    """
    response = send_request(user, course.id, "search", query_string)

    try:
        content = json.loads(response.content)
        collection = content["rows"]
    except (ValueError, KeyError):
        log.warning("invalid JSON: %s", response.content)
        raise EdxNotesParseError(_("Server error. Try again in a few minutes."))

    content.update({
        "rows": preprocess_collection(user, course, collection)
    })

    return json.dumps(content, cls=NoteJSONEncoder)


def get_notes(user, course):
    """
    Returns all notes for the user.
    """
    response = send_request(user, course.id, "annotations")

    try:
        collection = json.loads(response.content)
    except ValueError:
        return None

    # if collection is empty, just return it.
    if not collection:
        return None

    return json.dumps(preprocess_collection(user, course, collection), cls=NoteJSONEncoder)


def get_ancestor(store, usage_key):
    """
    Returns ancestor module for the passed `usage_key`.
    """
    location = store.get_parent_location(usage_key)
    if not location:
        log.warning("Parent location for the module not found: %s", usage_key)
        return
    try:
        return store.get_item(location)
    except ItemNotFoundError:
        log.warning("Parent module not found: %s", location)
        return


def get_ancestor_context(course, store, usage_key):
    """
    Returns dispay_name and url for the parent module.
    """
    parent = get_ancestor(store, usage_key)

    if not parent:
        return {
            u"display_name": None,
            u"url": None,
        }

    url = reverse("jump_to", kwargs={
        "course_id": course.id.to_deprecated_string(),
        "location": parent.location.to_deprecated_string(),
    })

    return {
        u"display_name": parent.display_name_with_default,
        u"url": url,
    }


def get_endpoint(path=""):
    """
    Returns endpoint.
    """
    interface = settings.EDXNOTES_INTERFACE if hasattr(settings, "EDXNOTES_INTERFACE") else False
    if interface and interface.get("url", False):
        url = interface["url"]
        if not url.endswith("/"):
            url += "/"

        if path:
            if path.startswith("/"):
                path = path.lstrip("/")
            if not path.endswith("/"):
                path += "/"

        return url + path
    else:
        raise ImproperlyConfigured(_("No endpoint was provided for EdxNotes."))


def generate_uid():
    """
    Generates unique id.
    """
    return uuid4().int  # pylint: disable=no-member


def is_feature_enabled(course):
    """
    Returns True if the edxnotes app is enabled for the course, False otherwise.

    In order for the app to be enabled it must be:
        1) enabled globally via FEATURES.
        2) present in the course tab configuration.
    """
    tab_found = next((True for t in course.tabs if t["type"] == "edxnotes"), False)
    feature_enabled = settings.FEATURES.get("ENABLE_EDXNOTES")

    return feature_enabled and tab_found
