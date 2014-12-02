"""
Views related to EdxNotes.
"""
import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.conf import settings
from edxmako.shortcuts import render_to_response
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from courseware.courses import get_course_with_access
from edxnotes.helpers import (
    get_endpoint,
    get_token,
    get_notes,
    is_feature_enabled
)
from xmodule.modulestore.django import modulestore
from util.json_request import JsonResponse, JsonResponseBadRequest
log = logging.getLogger(__name__)


@login_required
def edxnotes(request, course_id):
    """
    Displays the EdxNotes page.
    """
    course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    course = get_course_with_access(request.user, "load", course_key)

    if not is_feature_enabled(course):
        raise Http404

    notes = get_notes(request.user, course)
    context = {
        "course": course,
        "endpoint": get_endpoint(),
        "notes": notes,
        "token": get_token(request.user),
        "debug": json.dumps(settings.DEBUG),
    }

    return render_to_response("edxnotes.html", context)


def edxnotes_visibility(request, course_id):
    """
    Handle ajax call from "Show notes" checkbox.
    """
    course_key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    course = get_course_with_access(request.user, "load", course_key)

    if not is_feature_enabled(course):
        raise Http404

    try:
        edxnotes_visibility = json.loads(request.body)["visibility"]
        course.edxnotes_visibility = edxnotes_visibility
        modulestore().update_item(course, request.user.id)
        return JsonResponse(status=200)
    except ValueError:
        log.warning(
            "Could not decode request body as JSON and find a boolean visibility field: '{0}'".format(request.body)
        )
        return JsonResponseBadRequest()
