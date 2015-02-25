
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.core.validators import validate_email, validate_slug, ValidationError

from django.db import IntegrityError, transaction

from django_future.csrf import ensure_csrf_cookie
from django.http import (HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         Http404)
from django.shortcuts import redirect, get_object_or_404

from django.utils.translation import ugettext as _

from edxmako.shortcuts import render_to_response, render_to_string

from util.db import commit_on_success_with_read_committed
from util.json_request import JsonResponse

from collections import namedtuple

from student.views import _do_create_account, AccountValidationError
from student.models import (
    Registration, UserProfile, PendingNameChange,
    PendingEmailChange, CourseEnrollment, unique_id_for_user,
    CourseEnrollmentAllowed, UserStanding, LoginFailures,
    create_comments_service_user, PasswordHistory, UserSignupSource,
    DashboardConfiguration)

from company.models import Company

from courseware.courses import get_courses, sort_by_announcement
from courseware.access import has_access

from instructor.offline_gradecalc import student_grades

from xmodule.modulestore.django import modulestore
from xmodule.error_module import ErrorDescriptor

import dogstats_wrapper as dog_stats_api


@ensure_csrf_cookie
@login_required
def representative_dashboard(request):

    user = request.user

    if not user.profile.is_representative and not user.is_staff:
        return redirect(reverse('dashboard'))

    company = user.profile.company
    students = company.userprofile_set.filter(user__is_active__exact=1)

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

@ensure_csrf_cookie
@login_required
def staff_dashboard(request):
    """
    Staff dashboard page.

    :param request:
    :return:
    """
    if not request.user.is_staff:
        return redirect(reverse('dashboard'))

    context = {
        'companies': [
            {
                'id': company.id,
                'title': company.title,
                'representative': company.get_representative()
            }
            for company in Company.objects.all()
        ]
    }
    return render_to_response('company/staff_dashboard.html', context)

@ensure_csrf_cookie
@login_required
def add_company(request):
    """
    Add company page.

    :param request:
    :return:
    """
    company = Company()
    context = {
        'company': company
    }

    return render_to_response('company/company_edit.html', context)

@ensure_csrf_cookie
@login_required
def edit_company(request, company_id):
    """
    Edit company page.

    :param request:
    :param company_id:
    :return:
    """

    company_id = int(company_id)

    if company_id > 0:
        company = get_object_or_404(Company, id = company_id)
    else:
        company = Company()


    if request.method == 'POST':
        post_vars = request.POST

        company.title = post_vars['company_title']
        company.address = post_vars['company_address']
        company.real_address = post_vars['company_real_address']
        company.inn = post_vars['company_inn']
        company.kpk = post_vars['company_kpk']
        company.ceo_name = post_vars['company_ceo_name']
        company.email = post_vars['company_email']
        company.phone = post_vars['company_phone']
        company.save()

        return redirect(reverse('staff_edit_company', args=(company.id,)))


    context = {
        'company': company,
        'representative': company.get_representative(),
        'students': company.userprofile_set.filter(user__is_active=1)
    }

    return render_to_response('company/company_edit.html', context)

@ensure_csrf_cookie
@login_required
def company_progress(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    students = company.userprofile_set.filter(user__is_active__exact=1)

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

    return render_to_response('company/progress.html', context)

@ensure_csrf_cookie
@login_required
def set_representative(request, profile_id):
    profile = UserProfile.objects.get(id = profile_id)
    company = profile.company

    current_representative = company.get_representative()
    if current_representative:
        current_representative.is_representative = False
        current_representative.save()

    profile.is_representative = True
    profile.save()

    return redirect(reverse('staff_edit_company', args=(company.id,)))

@ensure_csrf_cookie
@login_required
def add_profile(request, company_id):
    js = {'success': False}

    post_vars = request.POST

    for req_field in ['username', 'password', 'name']:
        if req_field not in post_vars:
            js['value'] = _("Error (401 {field}). E-mail us.").format(field=req_field)
            js['field'] = req_field
            return JsonResponse(js, status=400)

    extra_fields = getattr(settings, 'REGISTRATION_EXTRA_FIELDS', {})

    if not 'email' in post_vars or not post_vars['email']:
        post_vars = dict(post_vars.items())
        post_vars.update(dict(email = post_vars['username'] + '@example.com'))

    required_post_vars = ['username', 'name', 'password']
    required_post_vars += [fieldname for fieldname, val in extra_fields.items()
                           if val == 'required']

    for field_name in required_post_vars:
        if field_name in ('gender', 'level_of_education'):
            min_length = 1
        else:
            min_length = 2

        if field_name not in post_vars or len(post_vars[field_name]) < min_length:
            error_str = {
                'username': _('Username must be minimum of two characters long'),
                'email': _('A properly formatted e-mail is required'),
                'name': _('Your legal name must be a minimum of two characters long'),
                'password': _('A valid password is required'),
                'terms_of_service': _('Accepting Terms of Service is required'),
                'honor_code': _('Agreeing to the Honor Code is required'),
                'level_of_education': _('A level of education is required'),
                'gender': _('Your gender is required'),
                'year_of_birth': _('Your year of birth is required'),
                'mailing_address': _('Your mailing address is required'),
                'goals': _('A description of your goals is required'),
                'city': _('A city is required'),
                'country': _('A country is required'),
                'phone': _('A phone is required'),
                'company_title': _('Company name is required')
            }

            if field_name in error_str:
                js['value'] = error_str[field_name]
            else:
                js['value'] = _('You are missing one or more required fields')

            js['field'] = field_name
            return JsonResponse(js, status=400)

        max_length = 75
        if field_name == 'username':
            max_length = 30

        if field_name in ('email', 'username') and len(post_vars[field_name]) > max_length:
            error_str = {
                'username': _('Username cannot be more than {num} characters long').format(num=max_length),
                'email': _('Email cannot be more than {num} characters long').format(num=max_length)
            }
            js['value'] = error_str[field_name]
            js['field'] = field_name
            return JsonResponse(js, status=400)

    try:
        validate_email(post_vars['email'])
    except ValidationError:
        js['value'] = _("Valid e-mail is required.")
        js['field'] = 'email'
        return JsonResponse(js, status=400)

    try:
        validate_slug(post_vars['username'])
    except ValidationError:
        js['value'] = _("Username should only consist of A-Z and 0-9, with no spaces.")
        js['field'] = 'username'
        return JsonResponse(js, status=400)

    username = post_vars['username']
    password = post_vars['password']
    if username == password:
        js['value'] = _("Username and password fields cannot match")
        js['field'] = 'username'
        return JsonResponse(js, status=400)

    # Ok, looks like everything is legit.  Create the account.
    try:
        with transaction.commit_on_success():
            ret = _do_create_account(post_vars, None)
    except AccountValidationError as exc:
        return JsonResponse({'success': False, 'value': exc.message, 'field': exc.field}, status=400)

    (user, profile, registration) = ret
    user.is_active = True
    user.save()

    dog_stats_api.increment("common.student.account_created")

    create_comments_service_user(user)

    response = JsonResponse({
        'success': True,
        'redirect_url': '',
    })

    # set the login cookie for the edx marketing site
    # we want this cookie to be accessed via javascript
    # so httponly is set to None

    if request.session.get_expire_at_browser_close():
        max_age = None
        expires = None
    else:
        max_age = request.session.get_expiry_age()
        expires_time = time.time() + max_age
        expires = cookie_date(expires_time)

    response.set_cookie(settings.EDXMKTG_COOKIE_NAME,
                        'true', max_age=max_age,
                        expires=expires, domain=settings.SESSION_COOKIE_DOMAIN,
                        path='/',
                        secure=None,
                        httponly=None)
    return response

@ensure_csrf_cookie
@login_required
def edit_profile(request, profile_id):
    profile = UserProfile.objects.get(id=profile_id)
    user = profile.user
    company = profile.company

    if request.method == 'GET':
        data = {
            'id': profile.id,
            'company_id': company.id,
            'email': user.email,
            'name': profile.name,
            'username': user.username,
            'phone': profile.phone,
            'city': profile.city,
            'mailing_address': profile.mailing_address,
            'country': profile.country.code,
            'gender': profile.gender,
        }
        return JsonResponse(data)

    js = {'success': False}
    post_vars = request.POST

    for req_field in ['username', 'email', 'name']:
        if req_field not in post_vars:
            js['value'] = _("Error (401 {field}). E-mail us.").format(field=req_field)
            js['field'] = req_field
            return JsonResponse(js, status=400)

    extra_fields = getattr(settings, 'REGISTRATION_EXTRA_FIELDS', {})

    required_post_vars = ['username', 'email', 'name']
    required_post_vars += [fieldname for fieldname, val in extra_fields.items()
                           if val == 'required']

    for field_name in required_post_vars:
        if field_name in ('gender', 'level_of_education'):
            min_length = 1
        else:
            min_length = 2

        if field_name not in post_vars or len(post_vars[field_name]) < min_length:
            error_str = {
                'username': _('Username must be minimum of two characters long'),
                'email': _('A properly formatted e-mail is required'),
                'name': _('Your legal name must be a minimum of two characters long'),
                'password': _('A valid password is required'),
                'terms_of_service': _('Accepting Terms of Service is required'),
                'honor_code': _('Agreeing to the Honor Code is required'),
                'level_of_education': _('A level of education is required'),
                'gender': _('Your gender is required'),
                'year_of_birth': _('Your year of birth is required'),
                'mailing_address': _('Your mailing address is required'),
                'goals': _('A description of your goals is required'),
                'city': _('A city is required'),
                'country': _('A country is required'),
                'phone': _('A phone is required'),
                'company_title': _('Company name is required')
            }

            if field_name in error_str:
                js['value'] = error_str[field_name]
            else:
                js['value'] = _('You are missing one or more required fields')

            js['field'] = field_name
            return JsonResponse(js, status=400)

        max_length = 75
        if field_name == 'username':
            max_length = 30

        if field_name in ('email', 'username') and len(post_vars[field_name]) > max_length:
            error_str = {
                'username': _('Username cannot be more than {num} characters long').format(num=max_length),
                'email': _('Email cannot be more than {num} characters long').format(num=max_length)
            }
            js['value'] = error_str[field_name]
            js['field'] = field_name
            return JsonResponse(js, status=400)

    try:
        validate_email(post_vars['email'])
    except ValidationError:
        js['value'] = _("Valid e-mail is required.")
        js['field'] = 'email'
        return JsonResponse(js, status=400)

    try:
        validate_slug(post_vars['username'])
    except ValidationError:
        js['value'] = _("Username should only consist of A-Z and 0-9, with no spaces.")
        js['field'] = 'username'
        return JsonResponse(js, status=400)

    username = post_vars['username']
    password = post_vars['password']
    if username == password:
        js['value'] = _("Username and password fields cannot match")
        js['field'] = 'username'
        return JsonResponse(js, status=400)

    # Ok, looks like everything is legit.  Create the account.
    try:
        with transaction.commit_on_success():

            user.email = post_vars['email']
            profile.name = post_vars['name']
            user.username = post_vars['username']
            profile.phone = post_vars['phone']
            profile.city = post_vars['city']
            profile.mailing_address = post_vars['mailing_address']
            profile.country = post_vars['country']
            profile.gender = post_vars['gender']
            if len(post_vars['password']) > 0:
                user.update_password(post_vars['password'])

            profile.save()
            user.save()

    except IntegrityError:
        # Figure out the cause of the integrity error
        msg = None
        field = None
        if len(User.objects.filter(username=post_vars['username'])) > 0:
            msg = _("An account with the Public Username '{username}' already exists.").format(username=post_vars['username'])
            field ="username"
        elif len(User.objects.filter(email=post_vars['email'])) > 0:
            msg = _("An account with the Email '{email}' already exists.").format(email=post_vars['email'])
            field = "email"
        else:
            raise
        return JsonResponse({'success': False, 'value': msg, 'field': field}, status=400)

    return JsonResponse({'success': True, 'redirect': reverse('staff_edit_company', args=(company.id,))})

@ensure_csrf_cookie
@login_required
def remove_profile(request, profile_id):
    profile = UserProfile.objects.get(id=profile_id)
    company = profile.company

    user = profile.user
    user.is_active = False
    user.save()

    return redirect(reverse('staff_edit_company', args=(company.id,)))