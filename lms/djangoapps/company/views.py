
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django_future.csrf import ensure_csrf_cookie
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404)
from django.shortcuts import redirect

from edxmako.shortcuts import render_to_response, render_to_string
from util.json_request import JsonResponse

from student.models import (
    Registration, UserProfile, PendingNameChange,
    PendingEmailChange, CourseEnrollment, unique_id_for_user,
    CourseEnrollmentAllowed, UserStanding, LoginFailures,
    create_comments_service_user, PasswordHistory, UserSignupSource,
    DashboardConfiguration)

from collections import namedtuple

from courseware.courses import get_courses, sort_by_announcement
from courseware.access import has_access

from instructor.offline_gradecalc import student_grades

from xmodule.modulestore.django import modulestore
from xmodule.error_module import ErrorDescriptor


@login_required
@ensure_csrf_cookie
def representative_dashboard(request):

    user = request.user

    if not user.profile.is_representative and not user.is_staff:
        return redirect(reverse('dashboard'))

    company = user.profile.company
    students = company.userprofile_set.all()

    courses_data = {}

    for student in students:
        enrollment_pairs = get_course_enrollment_pairs(student.user)
        for course, enrollment in enrollment_pairs:
            try:
                courses_data[enrollment.course_id]['students']
            except KeyError:
                courses_data[enrollment.course_id] = {
                    'course': course,
                    'students': []
                }

            courses_data[enrollment.course_id]['students'].append({
                'username': student.user.username,
                'id': student.user.id,
                'email': student.user.email,
                'real_name': student.name,
                'grades': student_grades(student.user, request, course)
            })

    context = {
        'company': company,
        'courses_data': courses_data
    }

    return render_to_response('company/representative_dashboard.html', context)


def get_course_enrollment_pairs(user):
    """
    Get enrollment pairs for user
    :param user:
    :return:
    """
    store = modulestore()

    for enrollment in CourseEnrollment.enrollments_for_user(user):
        with store.bulk_operations(enrollment.course_id):
            course = store.get_course(enrollment.course_id)
            if course and not isinstance(course, ErrorDescriptor):
                yield (course, enrollment)