// Search validation variables
let searchTimeout;
const MIN_SEARCH_LENGTH = 2;
const MAX_SEARCH_LENGTH = 30;

// Initialize all event listeners when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    try {
        initializeEventListeners();
        autoHideFlashMessages();
    } catch (error) {
        handleError('Failed to initialize page', error);
    }
});

// Initialize all event listeners
function initializeEventListeners() {
    try {
        // Profile mode toggle buttons
        const editProfileBtn = document.querySelector('[data-action="edit-profile"]');
        const changePasswordBtn = document.querySelector('[data-action="change-password"]');
        const cancelEditBtn = document.querySelector('[data-action="cancel-edit"]');
        const cancelPasswordBtn = document.querySelector('[data-action="cancel-password"]');
        
        if (editProfileBtn) editProfileBtn.addEventListener('click', toggleEditMode);
        if (changePasswordBtn) changePasswordBtn.addEventListener('click', togglePasswordMode);
        if (cancelEditBtn) cancelEditBtn.addEventListener('click', cancelEdit);
        if (cancelPasswordBtn) cancelPasswordBtn.addEventListener('click', cancelPasswordEdit);

        // Filter elements
        const statusFilter = document.getElementById('statusFilter');
        const categoryFilter = document.getElementById('categoryFilter');
        const searchInput = document.getElementById('searchReports');
        const clearFiltersBtn = document.querySelector('[data-action="clear-filters"]');

        if (statusFilter) statusFilter.addEventListener('change', filterReports);
        if (categoryFilter) categoryFilter.addEventListener('change', filterReports);
        if (clearFiltersBtn) clearFiltersBtn.addEventListener('click', clearFilters);

        // Search input events
        if (searchInput) {
            searchInput.addEventListener('keyup', function() {
                try {
                    validateSearchInput(this);
                } catch (error) {
                    handleError('Search validation failed', error);
                }
            });
            
            searchInput.addEventListener('input', function() {
                try {
                    handleSearchInput(this);
                } catch (error) {
                    handleError('Search input handling failed', error);
                }
            });
            
            searchInput.addEventListener('blur', function() {
                try {
                    validateSearchInput(this);
                } catch (error) {
                    handleError('Search validation failed', error);
                }
            });
        }

        // Report action buttons (View buttons)
        const viewButtons = document.querySelectorAll('[data-action="view-report"]');
        viewButtons.forEach(button => {
            button.addEventListener('click', function() {
                try {
                    const reportId = this.getAttribute('data-report-id');
                    if (reportId) {
                        viewReportDetails(reportId);
                    } else {
                        throw new Error('Report ID not found');
                    }
                } catch (error) {
                    handleError('Failed to view report details', error);
                }
            });
        });

        // Delete account button
        const deleteAccountBtn = document.querySelector('[data-action="delete-account"]');
        if (deleteAccountBtn) {
            deleteAccountBtn.addEventListener('click', deleteAccount);
        }

        // Modal close functionality
        const modalCloseBtn = document.querySelector('.close');
        const modal = document.getElementById('reportModal');
        
        if (modalCloseBtn) {
            modalCloseBtn.addEventListener('click', closeReportModal);
        }

        // Close modal when clicking outside
        if (modal) {
            modal.addEventListener('click', function(event) {
                if (event.target === modal) {
                    closeReportModal();
                }
            });
        }

    } catch (error) {
        handleError('Failed to initialize event listeners', error);
    }
}

// Error handling function
function handleError(message, error) {
    console.error(`${message}:`, error);
    
    // Show user-friendly error message
    const errorContainer = document.getElementById('alertContainer');
    if (errorContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-error';
        errorDiv.textContent = `${message}. Please try again or contact support if the problem persists.`;
        
        // Clear existing alerts and add new one
        errorContainer.innerHTML = '';
        errorContainer.appendChild(errorDiv);
        
        // Auto-hide error after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.remove();
            }
        }, 5000);
    }
}

// Profile mode functions
function toggleEditMode() {
    try {
        const viewMode = document.getElementById('viewMode');
        const editMode = document.getElementById('editMode');
        const passwordMode = document.getElementById('passwordMode');
        
        if (!viewMode || !editMode || !passwordMode) {
            throw new Error('Required mode elements not found');
        }
        
        viewMode.classList.remove('active');
        editMode.classList.add('active');
        passwordMode.classList.remove('active');
        clearAlerts();
    } catch (error) {
        handleError('Failed to toggle edit mode', error);
    }
}

function togglePasswordMode() {
    try {
        const viewMode = document.getElementById('viewMode');
        const editMode = document.getElementById('editMode');
        const passwordMode = document.getElementById('passwordMode');
        
        if (!viewMode || !editMode || !passwordMode) {
            throw new Error('Required mode elements not found');
        }
        
        viewMode.classList.remove('active');
        editMode.classList.remove('active');
        passwordMode.classList.add('active');
        clearAlerts();
    } catch (error) {
        handleError('Failed to toggle password mode', error);
    }
}

function cancelEdit() {
    try {
        const editMode = document.getElementById('editMode');
        const viewMode = document.getElementById('viewMode');
        
        if (!editMode || !viewMode) {
            throw new Error('Required mode elements not found');
        }
        
        editMode.classList.remove('active');
        viewMode.classList.add('active');
        clearAlerts();
    } catch (error) {
        handleError('Failed to cancel edit', error);
    }
}

function cancelPasswordEdit() {
    try {
        const passwordMode = document.getElementById('passwordMode');
        const viewMode = document.getElementById('viewMode');
        const passwordForm = document.getElementById('passwordForm');
        
        if (!passwordMode || !viewMode) {
            throw new Error('Required mode elements not found');
        }
        
        passwordMode.classList.remove('active');
        viewMode.classList.add('active');
        
        if (passwordForm) {
            passwordForm.reset();
        }
        clearAlerts();
    } catch (error) {
        handleError('Failed to cancel password edit', error);
    }
}

function clearAlerts() {
    try {
        const alertContainer = document.getElementById('alertContainer');
        if (alertContainer) {
            alertContainer.innerHTML = '';
        }
    } catch (error) {
        console.error('Failed to clear alerts:', error);
    }
}

// Search validation functions
function validateSearchInput(input) {
    try {
        if (!input) {
            throw new Error('Search input element not found');
        }

        const value = input.value.trim();
        const charCount = document.getElementById('searchCharCount');
        const validationMessage = document.getElementById('searchValidationMessage');
        
        if (!charCount || !validationMessage) {
            throw new Error('Search validation elements not found');
        }
        
        // Update character count
        charCount.textContent = `${value.length}/${MAX_SEARCH_LENGTH}`;
        
        // Clear previous validation styles
        input.classList.remove('input-error', 'input-warning', 'input-success');
        validationMessage.textContent = '';
        validationMessage.className = 'validation-message';
        
        // Validate input
        if (value.length === 0) {
            input.classList.add('input-success');
            validationMessage.textContent = 'Showing all reports';
            validationMessage.classList.add('success-message');
            return true;
        } else if (value.length < MIN_SEARCH_LENGTH) {
            input.classList.add('input-warning');
            validationMessage.textContent = `Enter at least ${MIN_SEARCH_LENGTH} characters to search`;
            validationMessage.classList.add('warning-message');
            return false;
        } else if (value.length > MAX_SEARCH_LENGTH) {
            input.classList.add('input-error');
            validationMessage.textContent = `Search term too long (max ${MAX_SEARCH_LENGTH} characters)`;
            validationMessage.classList.add('error-message');
            return false;
        } else if (!/^[a-zA-Z0-9\s\-_.,!?#()]*$/.test(value)) {
            input.classList.add('input-error');
            validationMessage.textContent = 'Only letters, numbers, spaces, and basic punctuation allowed';
            validationMessage.classList.add('error-message');
            return false;
        } else if (/^\s+$/.test(value)) {
            input.classList.add('input-warning');
            validationMessage.textContent = 'Search term cannot be only spaces';
            validationMessage.classList.add('warning-message');
            return false;
        } else {
            input.classList.add('input-success');
            validationMessage.textContent = `Searching for: "${value}"`;
            validationMessage.classList.add('success-message');
            return true;
        }
    } catch (error) {
        handleError('Search validation failed', error);
        return false;
    }
}

function handleSearchInput(input) {
    try {
        if (!input) {
            throw new Error('Search input element not found');
        }

        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // Update character count immediately
        const charCount = document.getElementById('searchCharCount');
        if (charCount) {
            charCount.textContent = `${input.value.length}/${MAX_SEARCH_LENGTH}`;
        }
        
        // Validate input
        const isValid = validateSearchInput(input);
        
        // Only perform search if input is valid or empty
        if (isValid || input.value.trim().length === 0) {
            searchTimeout = setTimeout(() => {
                try {
                    searchReports();
                } catch (error) {
                    handleError('Search failed', error);
                }
            }, 300);
        }
    } catch (error) {
        handleError('Search input handling failed', error);
    }
}

function sanitizeSearchInput(input) {
    try {
        if (typeof input !== 'string') {
            return '';
        }
        return input
            .trim()
            .replace(/\s+/g, ' ')
            .toLowerCase();
    } catch (error) {
        console.error('Failed to sanitize search input:', error);
        return '';
    }
}

// Filtering functions
function applyAllFilters() {
    try {
        const statusFilter = document.getElementById('statusFilter');
        const categoryFilter = document.getElementById('categoryFilter');
        const searchInput = document.getElementById('searchReports');
        const rows = document.querySelectorAll('#reportsTableBody tr');
        
        if (!statusFilter || !categoryFilter || !searchInput) {
            throw new Error('Filter elements not found');
        }
        
        const statusFilterValue = statusFilter.value.toLowerCase();
        const categoryFilterValue = categoryFilter.value.toLowerCase();
        const searchTerm = sanitizeSearchInput(searchInput.value);
        
        // Don't filter if search term is invalid
        if (searchTerm.length > 0 && !validateSearchInput(searchInput)) {
            return;
        }
        
        let visibleCount = 0;
        
        rows.forEach(row => {
            try {
                // Skip the "no reports" row
                if (row.cells.length === 1 && row.cells[0].colSpan === 7) {
                    return;
                }
                
                const status = row.getAttribute('data-status') || '';
                const category = row.getAttribute('data-category') || '';
                const title = (row.getAttribute('data-title') || '').toLowerCase();
                
                let showRow = true;
                
                // Status filter
                if (statusFilterValue && status !== statusFilterValue) {
                    showRow = false;
                }
                
                // Category filter
                if (categoryFilterValue && category !== categoryFilterValue) {
                    showRow = false;
                }
                
                // Search filter (TITLE ONLY)
                if (searchTerm && searchTerm.length >= MIN_SEARCH_LENGTH) {
                    const matchesSearch = title.includes(searchTerm);
                    if (!matchesSearch) {
                        showRow = false;
                    }
                }
                
                row.style.display = showRow ? '' : 'none';
                if (showRow) visibleCount++;
            } catch (error) {
                console.error('Error processing row:', error);
            }
        });
        
        // Update search validation message with results count
        if (searchTerm.length >= MIN_SEARCH_LENGTH) {
            const validationMessage = document.getElementById('searchValidationMessage');
            if (validationMessage) {
                validationMessage.textContent = `Found ${visibleCount} matching report${visibleCount !== 1 ? 's' : ''}`;
                validationMessage.className = 'validation-message success-message';
            }
        }
    } catch (error) {
        handleError('Failed to apply filters', error);
    }
}

function filterReports() {
    try {
        applyAllFilters();
    } catch (error) {
        handleError('Failed to filter reports', error);
    }
}

function searchReports() {
    try {
        applyAllFilters();
    } catch (error) {
        handleError('Failed to search reports', error);
    }
}

function clearFilters() {
    try {
        const statusFilter = document.getElementById('statusFilter');
        const categoryFilter = document.getElementById('categoryFilter');
        const searchInput = document.getElementById('searchReports');
        const charCount = document.getElementById('searchCharCount');
        const validationMessage = document.getElementById('searchValidationMessage');
        
        if (statusFilter) statusFilter.value = '';
        if (categoryFilter) categoryFilter.value = '';
        if (searchInput) searchInput.value = '';
        
        // Clear search validation
        if (searchInput) {
            searchInput.classList.remove('input-error', 'input-warning', 'input-success');
        }
        if (charCount) charCount.textContent = '0/30';
        if (validationMessage) {
            validationMessage.textContent = '';
            validationMessage.className = 'validation-message';
        }
        
        // Show all rows
        const rows = document.querySelectorAll('#reportsTableBody tr');
        rows.forEach(row => {
            row.style.display = '';
        });
    } catch (error) {
        handleError('Failed to clear filters', error);
    }
}

// Report details modal
function viewReportDetails(reportId) {
    try {
        if (!reportId) {
            throw new Error('Report ID is required');
        }

        const modal = document.getElementById('reportModal');
        if (!modal) {
            throw new Error('Report modal not found');
        }
        
        modal.style.display = 'block';
        
        // Show loading state
        const modalTitle = document.getElementById('modalReportTitle');
        const modalDescription = document.getElementById('modalReportDescription');
        
        if (modalTitle) modalTitle.textContent = 'Loading...';
        if (modalDescription) modalDescription.textContent = 'Loading report details...';
        
        // Fetch report details with error handling
        fetch(`/api/report/${encodeURIComponent(reportId)}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                populateModalWithReportData(data);
            })
            .catch(error => {
                handleError('Failed to load report details', error);
                modal.style.display = 'none';
            });
    } catch (error) {
        handleError('Failed to view report details', error);
    }
}

function populateModalWithReportData(data) {
    try {
        // Populate modal with report data
        const modalElements = {
            modalReportId: document.getElementById('modalReportId'),
            modalReportTitle: document.getElementById('modalReportTitle'),
            modalReportCategory: document.getElementById('modalReportCategory'),
            modalReportDescription: document.getElementById('modalReportDescription'),
            modalReportLocation: document.getElementById('modalReportLocation'),
            modalReportStatus: document.getElementById('modalReportStatus'),
            modalAdminComments: document.getElementById('modalAdminComments')
        };

        if (modalElements.modalReportId) {
            modalElements.modalReportId.textContent = '#' + (data.report_id || 'N/A');
        }
        if (modalElements.modalReportTitle) {
            modalElements.modalReportTitle.textContent = data.title || 'No title';
        }
        if (modalElements.modalReportCategory) {
            modalElements.modalReportCategory.textContent = data.category_name || 'No category';
        }
        if (modalElements.modalReportDescription) {
            modalElements.modalReportDescription.textContent = data.description || 'No description';
        }
        if (modalElements.modalReportLocation) {
            modalElements.modalReportLocation.textContent = data.location || 'Not specified';
        }
        
        // Update status with styling
        if (modalElements.modalReportStatus && data.status_name) {
            modalElements.modalReportStatus.textContent = '';
            const span = document.createElement('span');
            span.className = `status-${data.status_name.toLowerCase().replace(/\s+/g, '-')}`;
            span.textContent = data.status_name;
            modalElements.modalReportStatus.appendChild(span);
        }
        
        // Admin comments
        if (modalElements.modalAdminComments) {
            modalElements.modalAdminComments.textContent = data.admin_comments || 'No comments yet.';
        }
    } catch (error) {
        handleError('Failed to populate modal data', error);
    }
}

function closeReportModal() {
    try {
        const modal = document.getElementById('reportModal');
        if (modal) {
            modal.style.display = 'none';
        }
    } catch (error) {
        console.error('Failed to close modal:', error);
    }
}

// Delete account function
function deleteAccount() {
    try {
        const confirmed1 = confirm('Are you ABSOLUTELY sure you want to delete your account? This action cannot be undone and will permanently delete all your data including reports.');
        if (!confirmed1) return;

        const confirmed2 = confirm('This is your final warning. All your reports and data will be permanently lost. Continue?');
        if (!confirmed2) return;

        const confirmation = prompt('Type "DELETE" to confirm account deletion:');
        if (confirmation !== 'DELETE') {
            if (confirmation !== null) {
                alert('Account deletion cancelled. You must type "DELETE" exactly to confirm.');
            }
            return;
        }

        // Get CSRF token
        const csrfTokenMeta = document.querySelector('meta[name="csrf-token"]');
        if (!csrfTokenMeta) {
            throw new Error('CSRF token not found');
        }
        
        const csrfToken = csrfTokenMeta.getAttribute('content');
        
        // Send DELETE request using fetch
        fetch('/delete_account', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: 'csrf_token=' + encodeURIComponent(csrfToken)
        })
        .then(response => {
            if (response.ok) {
                window.location.href = '/login';
            } else {
                throw new Error('Server returned error status');
            }
        })
        .catch(error => {
            handleError('Failed to delete account', error);
        });
    } catch (error) {
        handleError('Account deletion failed', error);
    }
}

// Auto-hide flash messages
function autoHideFlashMessages() {
    try {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.style.display = 'none';
                }
            }, 5000);
        });
    } catch (error) {
        console.error('Failed to auto-hide flash messages:', error);
    }
}

// Legacy function support (for backward compatibility)
// These are kept for any remaining onclick attributes, but will be replaced by event listeners
window.toggleEditMode = toggleEditMode;
window.togglePasswordMode = togglePasswordMode;
window.cancelEdit = cancelEdit;
window.cancelPasswordEdit = cancelPasswordEdit;
window.filterReports = filterReports;
window.searchReports = searchReports;
window.clearFilters = clearFilters;
window.viewReportDetails = viewReportDetails;
window.closeReportModal = closeReportModal;
window.deleteAccount = deleteAccount;
window.validateSearchInput = validateSearchInput;
window.handleSearchInput = handleSearchInput;