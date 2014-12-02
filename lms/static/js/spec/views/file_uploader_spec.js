define(['backbone', 'jquery', 'js/models/file_uploader', 'js/views/file_uploader', 'js/common_helpers/template_helpers',
        'js/common_helpers/ajax_helpers', 'js/models/notification', 'string_utils'],
    function (Backbone, $, FileUploaderModel, FileUploaderView, TemplateHelpers, AjaxHelpers, NotificationModel) {
        describe("FileUploaderView", function () {
            var verifyTitle, verifyInputLabel, verifyInputTip, verifySubmitButton, verifyExtensions, verifyText,
                verifyFileUploadOption, verifyNotificationMessage, verifySubmitButtonEnabled, mimicUpload,
                respondWithSuccess, respondWithError, fileUploaderView, fileUploaderModel, url="http://test_url/";

            verifyText = function (css, expectedText) {
                expect(fileUploaderView.$(css).text().trim()).toBe(expectedText);
            };

            verifyTitle = function (expectedTitle) { verifyText('.form-title', expectedTitle); };

            verifyInputLabel = function (expectedLabel) { verifyText('.field-label', expectedLabel); };

            verifyInputTip = function (expectedTip) { verifyText('.tip', expectedTip); };

            verifySubmitButton = function (expectedButton) { verifyText('.submit-file-button', expectedButton); };

            verifyExtensions = function (expectedExtensions) {
                var acceptAttribute = fileUploaderView.$('input.input-file').attr('accept');
                if (expectedExtensions) {
                    expect(acceptAttribute).toBe(expectedExtensions);
                }
                else {
                    expect(acceptAttribute).toBe(undefined);
                }
            };

            verifySubmitButtonEnabled = function (expectedEnabled) {
                var submitButton = fileUploaderView.$('.submit-file-button');
                if (!expectedEnabled) {
                   expect(submitButton).toHaveClass("is-disabled");
                }
                else {
                   expect(submitButton).not.toHaveClass("is-disabled");
                }
            };

            verifyFileUploadOption = function (option, expectedValue) {
                expect(fileUploaderView.$('#file-upload-form').fileupload('option', option)).toBe(expectedValue);
            };

            verifyNotificationMessage = function (expectedMessage, type) {
                verifyText('.file-upload-form-result .message-' + type + ' .message-title', expectedMessage);
            };

            mimicUpload = function (test) {
                var requests = AjaxHelpers.requests(test);

                var param = {files: [{name: 'upload_file.txt'}]};
                fileUploaderView.$('#file-upload-form').fileupload('add', param);
                verifySubmitButtonEnabled(true);
                fileUploaderView.$('.submit-file-button').click();

                // No file will actually be uploaded because "uploaded_file.txt" doesn't actually exist.
                AjaxHelpers.expectRequest(requests, 'POST', url, new FormData());
                return requests;
            };

            respondWithSuccess = function (requests) {
                AjaxHelpers.respondWithJson(requests, {});
            };

            respondWithError = function (requests, errorMessage) {
                if (errorMessage) {
                    AjaxHelpers.respondWithErrorJson(requests, {error: errorMessage});
                }
                else {
                    AjaxHelpers.respondWithErrorJson(requests, {});
                }
            };

            beforeEach(function () {
                setFixtures("<div></div>");
                TemplateHelpers.installTemplate('templates/file-upload');
                TemplateHelpers.installTemplate('templates/instructor/instructor_dashboard_2/notification');
                fileUploaderModel = new FileUploaderModel({url: url});
                fileUploaderView = new FileUploaderView({model: fileUploaderModel}).render();
            });

            it('has default values', function () {
                verifyTitle("");
                verifyInputLabel("");
                verifyInputTip("");
                verifySubmitButton("Upload File");
                verifyExtensions(null);
                verifySubmitButtonEnabled(false);
            });

            it ('can set text values and extensions', function () {
                fileUploaderView = new FileUploaderView({
                    model: new FileUploaderModel({
                        title: "file upload title",
                        inputLabel: "test label",
                        inputTip: "test tip",
                        submitButtonText: "upload button text",
                        extensions: ".csv,.txt"
                    })
                }).render();

                verifyTitle("file upload title");
                verifyInputLabel("test label");
                verifyInputTip("test tip");
                verifySubmitButton("upload button text");
                verifyExtensions(".csv,.txt");
            });

            it ('can store upload URL', function () {
                expect(fileUploaderView.$('#file-upload-form').attr('action')).toBe(url);
            });

            it ('sets autoUpload to false', function () {
                verifyFileUploadOption('autoUpload', false);
            });

            it ('sets replaceFileInput to false', function () {
                verifyFileUploadOption('replaceFileInput', false);
            });

            it ('handles errors with default message', function () {
                var requests = mimicUpload(this);
                respondWithError(requests);
                verifyNotificationMessage("Your upload of 'upload_file.txt' failed.", "error");
            });

            it ('handles errors with custom message', function () {
                fileUploaderView = new FileUploaderView({
                    model: fileUploaderModel,
                    errorNotification: function (file, event, data) {
                        var message = interpolate_text("Custom error for '{file}'", {file: file});
                        return new NotificationModel({
                            type: "customized",
                            title: message
                        });
                    }
                }).render();
                var requests = mimicUpload(this);
                respondWithError(requests, "server error");
                verifyNotificationMessage("Custom error for 'upload_file.txt'", "customized");
            });

            it ('handles server error message', function () {
                var requests = mimicUpload(this);
                respondWithError(requests, "server error");
                verifyNotificationMessage("server error", "error");
            });

            it ('handles success with default message', function () {
                var requests = mimicUpload(this);
                respondWithSuccess(requests);
                verifyNotificationMessage("Your upload of 'upload_file.txt' succeeded.", "confirmation");
            });

            it ('handles success with custom message', function () {
                fileUploaderView = new FileUploaderView({
                    model: fileUploaderModel,
                    successNotification: function (file, event, data) {
                        var message = interpolate_text("Custom success message for '{file}'", {file: file});
                        return new NotificationModel({
                            type: "customized",
                            title: message
                        });
                    }
                }).render();
                var requests = mimicUpload(this);
                respondWithSuccess(requests);
                verifyNotificationMessage("Custom success message for 'upload_file.txt'", "customized");
            });
        });
    });
