from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import Http404, HttpResponseServerError
from util.json_request import JsonResponse
from opaque_keys.edx.keys import CourseKey
from courseware.access import has_access
from courseware.models import CoursePreference
from courseware.courses import get_course_by_id


@login_required
def set_access_expiration(request, course_id):
    try:
        course_key = CourseKey.from_string(course_id)
    except InvalidKeyError:
        log.error(u"Unable to find course with course key %s while loading the Instructor Dashboard.", course_id)
        return HttpResponseServerError()

    course = get_course_by_id(course_key, depth=0)
    if not has_access(request.user, 'staff', course):
        raise Http404()

    newValue = request.POST.get("access_expiration", "")
    CoursePreference.set_course_access_expiration_after(course_key, newValue)
    return JsonResponse({'course_access_expiration_after': CoursePreference.course_access_expiration_after(course_key)})


