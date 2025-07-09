// static/js/report_submission.js

document.addEventListener('DOMContentLoaded', function () {
    const categorySelect = document.getElementById('category');
    const otherContainer = document.getElementById('other-desc-container');
    const otherInput = document.getElementById('category_description');
    const alertContainer = document.getElementById('alertContainer');

    const fileUploadInput = document.getElementById('file-upload-input');
    const customFileUploadButton = document.getElementById('custom-file-upload-button');
    const filePreviewContainer = document.getElementById('file-preview-container');

    const reportForm = document.getElementById('report-form');
    const submitButton = reportForm.querySelector('button[type="submit"]');

    let selectedFiles = [];
    let rateLimitTimer = null;

    const MAX_ATTACHMENTS_PER_REPORT = 5;
    const MAX_TOTAL_UPLOAD_SIZE_MB = 5;

    // Helper to format file size
    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    // Function to get file icon class based on type/extension
    // Function to get file icon class based on type/extension
    function getFileIconClass(filename, mimetype) {
        const ext = filename.split('.').pop().toLowerCase();

        // Image files
        if (mimetype.startsWith('image/')) {
            return 'fa-file-image';
        }
        // Word documents
        else if (['doc', 'docx'].includes(ext) || mimetype === 'application/msword' || mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
            return 'fa-file-word';
        }
        // Excel spreadsheets
        else if (['xls', 'xlsx'].includes(ext) || mimetype === 'application/vnd.ms-excel' || mimetype === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
            return 'fa-file-excel';
        }
        // PowerPoint presentations
        else if (['ppt', 'pptx'].includes(ext) || mimetype === 'application/vnd.ms-powerpoint' || mimetype === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
            return 'fa-file-powerpoint';
        }
        // Archive files
        else if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext) || mimetype === 'application/zip' || mimetype === 'application/x-rar-compressed') {
            return 'fa-file-archive';
        }
        // Text files
        else if (['txt', 'log', 'csv'].includes(ext)) {
            return 'fa-file-lines';
        }
        // Fallback generic file icon
        return 'fa-file';
    }

    // Function to clear ALL alert messages from the container
    function clearAlerts() {
        if (alertContainer) {
            const alerts = alertContainer.querySelectorAll('.alert');
            alerts.forEach(alert => {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.5s ease-out';
                setTimeout(() => {
                    alert.remove();
                }, 500);
            });
        }
    }

    // Function to show a custom client-side flash message
    function showClientFlash(message, category = 'error') {
        if (alertContainer) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${category}`;
            alertDiv.textContent = message;
            alertContainer.appendChild(alertDiv);

            // Auto-hide this specific alert after 5 seconds
            setTimeout(() => {
                alertDiv.style.opacity = '0';
                alertDiv.style.transition = 'opacity 0.5s ease-out';
                setTimeout(() => {
                    alertDiv.remove();
                }, 500);
            }, 5000);
        }
    }

    // Function to set the visibility of the 'other' input
    function toggleOtherCategoryField() {
        if (categorySelect.value === 'other') {
            otherContainer.style.display = 'block';
        } else {
            otherContainer.style.display = 'none';
            otherInput.value = '';
        }
    }

    // Function to render all selected files in the preview container
    function renderFilePreviews() {
        filePreviewContainer.innerHTML = '';

        if (selectedFiles.length === 0) {
            filePreviewContainer.style.display = 'none';
            return;
        } else {
            filePreviewContainer.style.display = 'grid';
            filePreviewContainer.style.gridTemplateColumns = 'repeat(auto-fit, minmax(150px, 1fr))';
            filePreviewContainer.style.gap = '15px';
        }

        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            const fileTypeClass = file.type.split('/')[0];
            const fileExtensionClass = file.name.split('.').pop().toLowerCase();
            fileItem.className = `file-attachment-item type-${fileTypeClass} ext-${fileExtensionClass}`;
            fileItem.dataset.index = index;

            const iconClass = getFileIconClass(file.name, file.type);

            // Create icon element
            const icon = document.createElement('i');
            icon.className = `fa-solid ${iconClass} file-attachment-icon`;

            // Create text container
            const textContainer = document.createElement('div');
            textContainer.className = 'file-text-content';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'file-attachment-name';
            nameSpan.title = file.name;
            nameSpan.textContent = file.name;

            const sizeSpan = document.createElement('span');
            sizeSpan.className = 'file-attachment-size';
            sizeSpan.textContent = formatBytes(file.size);

            textContainer.appendChild(nameSpan);
            textContainer.appendChild(sizeSpan);

            // Create delete button
            const deleteButton = document.createElement('button');
            deleteButton.type = 'button';
            deleteButton.className = 'file-attachment-delete';
            deleteButton.dataset.index = index;

            const deleteIcon = document.createElement('i');
            deleteIcon.className = 'fa-solid fa-times';

            deleteButton.appendChild(deleteIcon);

            // Assemble file item
            fileItem.appendChild(icon);
            fileItem.appendChild(textContainer);
            fileItem.appendChild(deleteButton);

            filePreviewContainer.appendChild(fileItem);
        });

        filePreviewContainer.querySelectorAll('.file-attachment-delete').forEach(button => {
            button.addEventListener('click', deleteFile);
        });
    }

    // Function to handle file deletion
    function deleteFile(event) {
        const indexToDelete = parseInt(event.currentTarget.dataset.index);

        selectedFiles.splice(indexToDelete, 1);
        renderFilePreviews();
        clearAlerts();
    }

    // Event listener for the custom file upload button
    if (customFileUploadButton) {
        customFileUploadButton.addEventListener('click', () => {
            // NEW: Only allow click if not disabled
            if (!fileUploadInput.disabled) {
                fileUploadInput.click();
            }
        });
    }

    // Event listener for when files are selected via the hidden input
    if (fileUploadInput) {
        fileUploadInput.addEventListener('change', (event) => {
            const newFiles = Array.from(event.target.files);
            let currentTotalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);

            clearAlerts();

            for (const newFile of newFiles) {
                if (selectedFiles.length >= MAX_ATTACHMENTS_PER_REPORT) {
                    showClientFlash(`You can only upload a maximum of ${MAX_ATTACHMENTS_PER_REPORT} files.`, 'error');
                    break; // Stop adding files if limit reached
                }

                if ((currentTotalSize + newFile.size) > MAX_TOTAL_UPLOAD_SIZE_MB * 1024 * 1024) {
                    showClientFlash(`Total upload size exceeds the maximum allowed of ${MAX_TOTAL_UPLOAD_SIZE_MB}MB. Please reduce the number of files and try again.`, 'error');
                    continue;
                }

                const allowedExtensions = ['png', 'jpg', 'jpeg', 'gif'];
                const fileExtension = newFile.name.split('.').pop().toLowerCase();
                if (!allowedExtensions.includes(fileExtension)) {
                    showClientFlash(`File '${newFile.name}' has an unsupported file type. Allowed types are ${allowedExtensions.join(', ')}.`, 'error');
                    continue;
                }

                if (selectedFiles.some(f => f.name === newFile.name && f.size === newFile.size)) {
                    showClientFlash(`File '${newFile.name}' is already added.`, 'error');
                    continue;
                }

                selectedFiles.push(newFile);
                currentTotalSize += newFile.size;
            }

            renderFilePreviews();
            event.target.value = '';
        });
    }

    // Function for client-side content validation
    function containsInvalidCharsClient(value) {
        if (/<script\b[^>]*>.*?<\/script>/i.test(value)) return true;
        if (/onerror=|onload=|javascript:|data:text\/html/i.test(value)) return true;
        if (/SELECT\s| FROM\s| INSERT\s| UPDATE\s| DELETE\s| OR\s| AND\s| UNION\s| EXEC\s/i.test(value)) return true;
        if (/<|>/.test(value)) return true;
        if (/[\x00-\x1F\x7F]/.test(value)) return true;

        return false;
    }

    // NEW: Function to disable the form elements
    function disableForm(durationSeconds = 0) {
        reportForm.querySelectorAll('input, select, textarea, button').forEach(element => {
            // Keep submit button separate for countdown text handling
            if (element !== submitButton) {
                element.disabled = true;
            }
            // Add a class for visual feedback (e.g., grey out)
            element.classList.add('disabled-form-element');
        });

        // Disable delete file buttons too
        filePreviewContainer.querySelectorAll('.file-attachment-delete').forEach(button => {
            button.disabled = true;
        });

        submitButton.disabled = true; // Disable submit button

        if (durationSeconds > 0) {
            let timeLeft = durationSeconds;
            // Clear any existing timer before setting a new one
            if (rateLimitTimer) {
                clearInterval(rateLimitTimer);
            }

            submitButton.textContent = `Please wait (${timeLeft}s)`;
            rateLimitTimer = setInterval(() => {
                timeLeft--;
                if (timeLeft > 0) {
                    submitButton.textContent = `Please wait (${timeLeft}s)`;
                } else {
                    clearInterval(rateLimitTimer);
                    rateLimitTimer = null; // Clear the timer ID
                    enableForm();
                    showClientFlash("You can submit reports again now.", 'info');
                }
            }, 1000);
        } else {
            submitButton.textContent = "Submitting..."; // For general submission state
        }
    }

    // NEW: Function to enable the form elements
    function enableForm() {
        // Only enable if no active rate limit timer
        if (rateLimitTimer) return;

        reportForm.querySelectorAll('input, select, textarea, button').forEach(element => {
            element.disabled = false;
            element.classList.remove('disabled-form-element');
        });

        // Enable delete file buttons
        filePreviewContainer.querySelectorAll('.file-attachment-delete').forEach(button => {
            button.disabled = false;
        });

        submitButton.textContent = "Submit Report"; // Reset button text
    }

    // Handle form submission
    if (reportForm) {
        reportForm.addEventListener('submit', async function (event) {
            event.preventDefault();

            // Clear ALL previous alerts at the start of a new submission attempt
            clearAlerts();
            // NEW: Disable form immediately on submit to prevent double clicks/submissions
            disableForm();

            // CLIENT-SIDE VALIDATION BEFORE SUBMISSION
            const title = this.elements.title.value;
            const trimmedTitle = title.trim();

            const description = this.elements.description.value;
            const trimmedDescription = description.trim();

            const categoryValue = this.elements.category.value;

            const categoryDescription = this.elements.category_description.value;
            const trimmedCategoryDescription = categoryDescription.trim();

            const clientValidationErrors = [];

            // Title Validation
            if (!trimmedTitle) {
                clientValidationErrors.push("Title cannot be empty.");
            }
            if (trimmedTitle.length > 255) {
                clientValidationErrors.push("Title must be 255 characters or less.");
            }
            if (containsInvalidCharsClient(title)) {
                clientValidationErrors.push("Title contains invalid characters.");
            }

            // Description Validation
            if (!trimmedDescription) {
                clientValidationErrors.push("Description cannot be empty.");
            }
            if (trimmedDescription.length > 1000) {
                clientValidationErrors.push("Description must be 1000 characters or less.");
            }
            if (containsInvalidCharsClient(description)) {
                clientValidationErrors.push("Description contains invalid characters.");
            }

            // Category Validation
            if (categoryValue === 'other') {
                if (!trimmedCategoryDescription) {
                    clientValidationErrors.push("Category description cannot be empty.");
                }
                if (trimmedCategoryDescription.length > 255) {
                    clientValidationErrors.push("Category description must be 255 characters or less.");
                }
                if (containsInvalidCharsClient(categoryDescription)) {
                    clientValidationErrors.push("Category description contains invalid characters.");
                }
            } else if (!categoryValue) {
                clientValidationErrors.push("Category cannot be empty.");
            }


            // If client-side errors, display them and stop the submission
            if (clientValidationErrors.length > 0) {
                const uniqueErrors = new Set(clientValidationErrors);
                uniqueErrors.forEach(msg => showClientFlash(msg, 'error'));
                // NEW: Re-enable form if client-side validation fails
                enableForm();
                return; // Stop form submission here
            }
            // END CLIENT-SIDE VALIDATION

            const formData = new FormData();

            // Append trimmed values to FormData, as these are what Flask expects for database storage.
            // Server-side validation will also trim them.
            formData.append('csrf_token', this.elements.csrf_token.value);
            formData.append('title', trimmedTitle);
            formData.append('description', trimmedDescription);
            formData.append('category', categoryValue);

            if (categoryValue === 'other') {
                formData.append('category_description', trimmedCategoryDescription);
            }
            if (this.elements.anonymous.checked) {
                formData.append('anonymous', '1');
            }

            selectedFiles.forEach(file => {
                formData.append('attachments', file, file.name);
            });

            try {
                const response = await fetch(this.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const responseText = await response.text();
                let result;
                try {
                    result = JSON.parse(responseText);
                } catch (e) {
                    // If parsing fails, it might be a direct redirect or non-JSON error page
                    if (response.redirected) {
                        window.location.href = response.url;
                    } else {
                        // Fallback: if we get non-JSON and not a redirect, assume a server-rendered error page
                        // and reload to show any flash messages Flask might have rendered.
                        window.location.reload();
                    }
                    return;
                }

                if (response.ok) {
                    if (result && result.redirect) {
                        window.location.href = result.redirect;
                    } else {
                        window.location.href = '/';
                    }
                } else {
                    // This handles server-side validation errors AND rate limits
                    if (result && result.error_messages) {
                        const uniqueServerErrors = new Set(result.error_messages);
                        uniqueServerErrors.forEach(msg => showClientFlash(msg, 'error'));

                        // NEW: Check for rate limit response and duration
                        if (response.status === 429 && result.retry_after) {
                            disableForm(result.retry_after); // Disable and set timer
                        } else {
                            enableForm(); // For other errors, re-enable immediately
                        }
                    } else if (result && result.message) {
                        showClientFlash(result.message, 'error');
                        enableForm(); // Re-enable for generic messages
                    } else {
                        showClientFlash('An unexpected server error occurred. Please try again.', 'error');
                        enableForm(); // Re-enable for unknown errors
                    }
                }
            } catch (error) {
                console.error('Network error during form submission:', error); // Keep this as it indicates a critical network issue
                showClientFlash('Network error or server unreachable. Please try again.', 'error');
                enableForm(); // Re-enable on network errors
            }
        });
    }

    // Initial setup
    if (categorySelect) {
        toggleOtherCategoryField();
        categorySelect.addEventListener('change', () => {
            toggleOtherCategoryField();
            clearAlerts();
        });
    }

    // Auto-hide flash messages (for those initially rendered by Flask on page load)
    const initialAlerts = document.querySelectorAll('#alertContainer .alert');
    initialAlerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.5s ease-out';
            setTimeout(() => {
                alert.style.display = 'none';
                alert.remove();
            }, 500);
        }, 5000);
    });
});