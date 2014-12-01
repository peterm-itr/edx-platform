;(function (define, undefined) {
    'use strict';
    define(['jquery', 'underscore', 'js/edxnotes/views/edxnotes_wrapper_factory'], function($, _, EdxnotesWrapperFactory) {
        return function (visibility, visibilityUrl) {
            var checkbox = $('p.action-inline > a.action-toggle-notes'),
                checkboxIcon = checkbox.children('i.checkbox-icon');

            checkbox.on('click', function(event) {
                visibility = !visibility;
                toggleAnnotator();

                $.ajax({
                    type: 'PUT',
                    url: window.location.origin + visibilityUrl,
                    contentType: 'application/json',
                    dataType: 'json',
                    data: JSON.stringify({'visibility': visibility}),
                    error: function(response) {
                        console.log(JSON.parse(response.responseText));
                    }
                });
                event.preventDefault();
            });

            function toggleCheckbox() {
                checkboxIcon.toggleClass('icon-check', visibility)
                            .toggleClass('icon-check-empty', !visibility);
            }

            function toggleAnnotator() {
                toggleCheckbox();
                if (visibility) {
                    _.each($('.edx-notes-wrapper'),  EdxnotesWrapperFactory.createAnnotator);
                } else {
                    EdxnotesWrapperFactory.destroyAllInstances();
                }
            }
        };
    });
}).call(this, define || RequireJS.define);
