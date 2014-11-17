"""
The Enrollment API Views should be simple, lean HTTP endpoints for API access. This should
consist primarily of authentication, request validation, and serialization.

"""
from rest_framework import status
from rest_framework.authentication import OAuth2Authentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from enrollment import api
from student.models import NonExistentCourseError, CourseEnrollmentException


class EnrollmentUserThrottle(UserRateThrottle):
    """Limit the number of requests users can make to the enrollment API."""
    # TODO Limit significantly after performance testing.  # pylint: disable=fixme
    rate = '50/second'


class SessionAuthenticationAllowInactiveUser(SessionAuthentication):
    """Ensure that the user is logged in, but do not require the account to be active.

    We use this in the special case that a user has created an account,
    but has not yet activated it.  We still want to allow the user to
    enroll in courses, so we remove the usual restriction
    on session authentication that requires an active account.

    You should use this authentication class ONLY for end-points that
    it's safe for an unactived user to access.  For example,
    we can allow a user to update his/her own enrollments without
    activating an account.

    """
    def authenticate(self, request):
        """Authenticate the user, requiring a logged-in account and CSRF.

        This is exactly the same as the `SessionAuthentication` implementation,
        with the `user.is_active` check removed.

        Args:
            request (HttpRequest)

        Returns:
            Tuple of `(user, token)`

        Raises:
            PermissionDenied: The CSRF token check failed.

        """
        # Get the underlying HttpRequest object
        request = request._request  # pylint: disable=protected-access
        user = getattr(request, 'user', None)

        # Unauthenticated, CSRF validation not required
        # This is where regular `SessionAuthentication` checks that the user is active.
        # We have removed that check in this implementation.
        if not user:
            return None

        self.enforce_csrf(request)

        # CSRF passed with authenticated user
        return (user, None)


class EnrollmentView(APIView):
    """ Enrollment API View for creating, updating, and viewing course enrollments. """

    authentication_classes = OAuth2Authentication, SessionAuthenticationAllowInactiveUser
    permission_classes = IsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    def get(self, request, course_id=None):
        """Create, read, or update enrollment information for a student.

        HTTP Endpoint for all CRUD operations for a student course enrollment. Allows creation, reading, and
        updates of the current enrollment for a particular course.

        Args:
            request (Request): To get current course enrollment information, a GET request will return
                information for the current user and the specified course.
            course_id (str): URI element specifying the course location. Enrollment information will be
                returned, created, or updated for this particular course.

        Return:
            A JSON serialized representation of the course enrollment.

        """
        try:
            return Response(api.get_enrollment(request.user.username, course_id))
        except (NonExistentCourseError, CourseEnrollmentException):
            return Response(status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, course_id=None):
        """Update the course enrollment.

        HTTP Endpoint for all creation and modifications to an existing enrollment.

        Args:
            request (Request): A PUT request create or modify an existing enrollment. If 'mode' or 'deactivate'
                are found in the request parameters, the mode can be modified, or the enrollment can be
                deactivated.
            course_id (str): URI element specifying the course location. Enrollment information will be
                returned, created, or updated for this particular course.

        Return:
            A JSON serialized representation of the course enrollment, including all modifications.
        """
        try:
            if 'mode' in request.DATA:
                return Response(api.update_enrollment(request.user.username, course_id, request.DATA['mode']))
            elif 'deactivate' in request.DATA:
                return Response(api.deactivate_enrollment(request.user.username, course_id))
            else:
                return Response(api.add_enrollment(request.user.username, course_id))
        except api.CourseModeNotFoundError as error:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=error.data)
        except (NonExistentCourseError, api.EnrollmentNotFoundError, CourseEnrollmentException):
            return Response(status=status.HTTP_400_BAD_REQUEST)


class EnrollmentListView(APIView):
    """ Enrollment API List View for viewing all course enrollments for a student. """

    authentication_classes = OAuth2Authentication, SessionAuthenticationAllowInactiveUser
    permission_classes = IsAuthenticated,
    throttle_classes = EnrollmentUserThrottle,

    def get(self, request):
        """List out all the enrollments for the current student

        Returns a JSON response with all the course enrollments for the current student.

        Args:
            request (Request): The GET request for course enrollment listings.

        Returns:
            A JSON serialized representation of the student's course enrollments.

        """
        return Response(api.get_enrollments(request.user.username))
