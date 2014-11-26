from django.conf.urls import include, patterns, url
from django.conf import settings

from django.views.generic import TemplateView

from course_modes import views

urlpatterns = patterns(
    '',
    # pylint seems to dislike as_view() calls because it's a `classonlymethod` instead of `classmethod`, so we disable the warning
    url(r'^choose/{}/$'.format(settings.COURSE_ID_PATTERN), views.ChooseModeView.as_view(), name="course_modes_choose"),  # pylint: disable=no-value-for-parameter
)

if settings.FEATURES["CONVERT_TO_PAID_CERTIFICATE_COURSE_MODE_FOR_TESTING"]:
    urlpatterns += (
        url(r'^add_honor_mode_to_course/$', views.add_honor_mode_to_course),
    )
