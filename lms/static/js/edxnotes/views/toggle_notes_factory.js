;(function (define, undefined) {
    'use strict';
    define([
        'jquery', 'underscore', 'js/edxnotes/views/edxnotes_visibility_decorator'
    ], function($, _, EdxnotesVisibilityDecorator) {
        return function (visibility, visibilityUrl) {
            var checkbox = $('p.action-inline > a.action-toggle-notes'),
                checkboxIcon = checkbox.children('i.checkbox-icon'),
                toggleCheckbox, toggleAnnotator, sendRequest;

            toggleCheckbox = function () {
                checkboxIcon.removeClass('icon-check icon-check-empty');
                checkboxIcon.addClass(visibility ? 'icon-check' : 'icon-check-empty');
            };

            toggleAnnotator = function () {
                toggleCheckbox();
                if (visibility) {
                    $('.edx-notes-wrapper').each(function () {
                        EdxnotesVisibilityDecorator.enableNote(this)
                    });
                } else {
                    EdxnotesVisibilityDecorator.disableNotes();
                }
            };

            sendRequest = function () {
                return $.ajax({
                    type: 'PUT',
                    url: window.location.origin + visibilityUrl,
                    dataType: 'json',
                    data: JSON.stringify({'visibility': visibility}),
                    error: function(response) {
                        console.log(JSON.parse(response.responseText));
                    }
                });
            };

            checkbox.on('click', function (event) {
                visibility = !visibility;
                toggleAnnotator();
                sendRequest();
                event.preventDefault();
            });
        };
    });
}).call(this, define || RequireJS.define);
