// static/js/report_submission.js

document.addEventListener('DOMContentLoaded', function () {
    const categorySelect = document.getElementById('category');
    const otherContainer = document.getElementById('other-desc-container');
    const otherInput = document.getElementById('category_description');
    const alertContainer = document.getElementById('alertContainer'); // Get the alert container

    // New attachment related elements
    const fileUploadInput = document.getElementById('file-upload-input');
    const customFileUploadButton = document.getElementById('custom-file-upload-button');
    const filePreviewContainer = document.getElementById('file-preview-container');

    // Store files globally, this will be the source of truth for files to be submitted
    let selectedFiles = [];

    // Constants for file limits (should match Flask MAX_ATTACHMENTS_PER_REPORT, etc.)
    const MAX_ATTACHMENTS_PER_REPORT = 5;
    const MAX_SINGLE_FILE_SIZE_MB = 2; // MB
    const MAX_TOTAL_UPLOAD_SIZE_MB = 10; // MB

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
    function getFileIconClass(filename, mimetype) {
        const ext = filename.split('.').pop().toLowerCase();
        // Prioritize specific MIME types or common extensions
        if (mimetype === 'application/pdf' || ext === 'pdf') {
            return 'fa-file-pdf'; // PDF icon
        } else if (mimetype.startsWith('image/')) {
            return 'fa-file-image'; // Image icon
        } else if (['doc', 'docx'].includes(ext) || mimetype === 'application/msword' || mimetype === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
            return 'fa-file-word'; // Word Document icon
        } else if (['xls', 'xlsx'].includes(ext) || mimetype === 'application/vnd.ms-excel' || mimetype === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') {
            return 'fa-file-excel'; // Excel icon
        } else if (['ppt', 'pptx'].includes(ext) || mimetype === 'application/vnd.ms-powerpoint' || mimetype === 'application/vnd.openxmlformats-officedocument.presentationml.presentation') {
            return 'fa-file-powerpoint'; // PowerPoint icon
        } else if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext) || mimetype === 'application/zip' || mimetype === 'application/x-rar-compressed') {
            return 'fa-file-archive'; // Archive icon
        } else if (['txt', 'log', 'csv'].includes(ext)) { // Generic text files
            return 'fa-file-alt'; // Or 'fa-file-lines' for text
        }
        return 'fa-file'; // Generic file icon for anything else
    }


    // Function to clear alert messages
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
        clearAlerts(); // Clear existing alerts before showing new one
        if (alertContainer) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${category}`;
            alertDiv.textContent = message;
            alertContainer.appendChild(alertDiv);

            // Auto-hide the newly created alert
            setTimeout(() => {
                alertDiv.style.opacity = '0';
                alertDiv.style.transition = 'opacity 0.5s ease-out';
                setTimeout(() => {
                    alertDiv.remove();
                }, 500);
            }, 5000); // Hide after 5 seconds
        }
    }

    // Function to set the visibility of the 'other' input
    function toggleOtherCategoryField() {
        if (categorySelect.value === 'other') {
            otherContainer.style.display = 'block';
        } else {
            otherContainer.style.display = 'none';
            otherInput.value = ''; // Clear value if category changes from 'other'
        }
    }

    // Function to render all selected files in the preview container
    function renderFilePreviews() {
        filePreviewContainer.innerHTML = ''; // Clear existing previews

        if (selectedFiles.length === 0) {
            filePreviewContainer.style.display = 'none';
            return;
        } else {
            filePreviewContainer.style.display = 'flex'; // Ensure container is visible
        }

        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            const fileTypeClass = file.type.split('/')[0];
            const fileExtensionClass = file.name.split('.').pop().toLowerCase();
            fileItem.className = `file-attachment-item type-${fileTypeClass} ext-${fileExtensionClass}`;
            fileItem.dataset.index = index; // Store index for easy deletion

            const iconClass = getFileIconClass(file.name, file.type);

            // MODIFIED HTML STRUCTURE HERE
            fileItem.innerHTML = `
                <i class="fa-solid ${iconClass} file-attachment-icon"></i>
                <div class="file-text-content">
                    <span class="file-attachment-name" title="${file.name}">${file.name}</span>
                    <span class="file-attachment-size">${formatBytes(file.size)}</span>
                </div>
                <button type="button" class="file-attachment-delete" data-index="${index}">
                    <i class="fa-solid fa-times"></i>
                </button>
            `;
            filePreviewContainer.appendChild(fileItem);
        });

        // Attach event listeners to new delete buttons
        filePreviewContainer.querySelectorAll('.file-attachment-delete').forEach(button => {
            button.addEventListener('click', deleteFile);
        });
    }

    // Function to handle file deletion
    function deleteFile(event) {
        const indexToDelete = parseInt(event.currentTarget.dataset.index);

        // Remove file from our JavaScript array
        selectedFiles.splice(indexToDelete, 1);

        // Re-render previews to update indices and display
        renderFilePreviews();

        // Update the hidden file input to reflect the changes
        updateFileInput();

        clearAlerts(); // Clear alerts after a successful delete action
    }

    // Function to update the hidden file input's files property
    // This is crucial for form submission
    function updateFileInput() {
        const dataTransfer = new DataTransfer();
        selectedFiles.forEach(file => {
            dataTransfer.items.add(file);
        });
        fileUploadInput.files = dataTransfer.files;
    }

    // Event listener for the custom file upload button
    if (customFileUploadButton) {
        customFileUploadButton.addEventListener('click', () => {
            fileUploadInput.click(); // Trigger click on the hidden file input
        });
    }

    // Event listener for when files are selected via the hidden input
    if (fileUploadInput) {
        fileUploadInput.addEventListener('change', (event) => {
            const newFiles = Array.from(event.target.files);
            let currentTotalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);

            clearAlerts(); // Clear any existing alerts before processing new files

            for (const newFile of newFiles) {
                // Check max attachments limit
                if (selectedFiles.length >= MAX_ATTACHMENTS_PER_REPORT) {
                    showClientFlash(`You can only upload a maximum of ${MAX_ATTACHMENTS_PER_REPORT} files. Skipping additional files.`, 'error');
                    break; // Stop adding files if limit reached
                }

                // Check single file size limit
                if (newFile.size > MAX_SINGLE_FILE_SIZE_MB * 1024 * 1024) {
                    showClientFlash(`File '${newFile.name}' exceeds the maximum allowed size of ${MAX_SINGLE_FILE_SIZE_MB}MB. Skipping this file.`, 'error');
                    continue; // Skip this file, try next
                }

                // Check total upload size limit
                if ((currentTotalSize + newFile.size) > MAX_TOTAL_UPLOAD_SIZE_MB * 1024 * 1024) {
                    showClientFlash(`Total upload size exceeds the maximum allowed of ${MAX_TOTAL_UPLOAD_SIZE_MB}MB. File '${newFile.name}' was not added.`, 'error');
                    continue; // Skip this file, try next
                }

                // Check allowed file types (can be redundant if Flask also checks, but good for UX)
                const allowedExtensions = ['png', 'jpg', 'jpeg', 'gif', 'pdf']; // Match your Python ALLOWED_EXTENSIONS
                const fileExtension = newFile.name.split('.').pop().toLowerCase();
                if (!allowedExtensions.includes(fileExtension)) {
                    showClientFlash(`File '${newFile.name}' has an unsupported file type. Allowed types are ${allowedExtensions.join(', ')}.`, 'error');
                    continue;
                }

                // If all checks pass, add the file
                selectedFiles.push(newFile);
                currentTotalSize += newFile.size; // Update total size
            }

            renderFilePreviews(); // Re-render all previews
            updateFileInput(); // Update the hidden input to reflect new selectedFiles

            // Reset the file input's value to allow selecting the same file again if needed
            event.target.value = '';
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

    // Auto-hide flash messages (for those initially rendered by Flask)
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

    // We no longer prevent default submission in JS for empty field checks.
    // The server-side Python handles all validation and error flashing comprehensively.
});