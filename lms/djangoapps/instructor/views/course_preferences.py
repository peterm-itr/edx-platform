from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseServerError
from util.json_request import JsonResponse
from opaque_keys.edx.keys import CourseKey
from courseware.access import has_access
from courseware.models import CoursePreference
from courseware.courses import get_course_by_id
from datetime import datetime, timedelta
from student.models import CourseEnrollment


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


@login_required
def refresh_enrollment(request, course_id):
    try:
        course_key = CourseKey.from_string(course_id)
    except InvalidKeyError:
        log.error(u"Unable to find course with course key %s while loading the Instructor Dashboard.", course_id)
        return HttpResponseServerError()

    course = get_course_by_id(course_key, depth=0)
    if not has_access(request.user, 'staff', course):
        raise Http404()

    enrollment_id = int(request.POST.get('enrollment_id'))

    course_access_expiration = CoursePreference.course_access_expiration_after(course_key)
    new_expiration_date = datetime.now() + timedelta(days=course_access_expiration)

    enrollment = CourseEnrollment.objects.get(id=enrollment_id)
    enrollment.created = datetime.now()
    enrollment.save()

    return JsonResponse({'expired': new_expiration_date.strftime("%d.%m.%Y")})
