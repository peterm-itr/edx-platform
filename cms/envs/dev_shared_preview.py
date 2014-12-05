"""
This configuration is have localdev use a preview.localhost hostname for the preview LMS so that we can share
the same process between preview and published
"""

# We intentionally define lots of variables that aren't used, and
# want to import all variables from base settings files
# pylint: disable=wildcard-import, unused-wildcard-import

from .dev import *

FEATURES['PREVIEW_LMS_BASE'] = "preview.localhost:8000"
