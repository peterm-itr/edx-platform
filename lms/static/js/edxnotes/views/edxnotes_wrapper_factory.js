;(function (define, undefined) {
    'use strict';
    define(['jquery', 'underscore', 'js/edxnotes/views/notes'], function($, _, Notes) {
        var _params = null, _visibility = null,
            cleanup = function(ids) {
                var len = Annotator._instances.length;
                while (len--) {
                    if (!_.contains(ids, Annotator._instances[len].element.attr('id'))) {
                        Annotator._instances[len].destroy();
                    }
                }
            },
            getIds = function() {
                return _.map($('.edx-notes-wrapper'), function (element) {
                    return element.id;
                });
            },
            createAnnotator = function(element) {
                console.time(element);
                Notes.factory(element, _params);
                console.timeEnd(element);
            },
            destroyAllInstances = function() {
                var len = Annotator._instances.length;
                while (len--) {
                    Annotator._instances[len].destroy();
                }
            },
            factory = function (elementId, params, visibility) {
                var element = $('#'+elementId).get(0);

                if (_.isNull(_params)) {
                    _params = params;
                }
                if (_.isNull(_visibility)) {
                    _visibility = visibility;
                }
                if (_visibility) {
                    // When switching sequentials, the global object Annotator still keeps track of the previous
                    // instances that were created in an array called 'Annotator._instances'. We have to destroy these
                    // but keep those found on page being loaded (for the case when there are more than one HTML
                    // component per vertical).
                    cleanup(getIds());
                    createAnnotator(element);
                }
            };
        return {
            factory: factory,
            createAnnotator: createAnnotator,
            destroyAllInstances: destroyAllInstances
        }
    });
}).call(this, define || RequireJS.define);
