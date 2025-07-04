// Function to toggle section visibility with animation
function toggleSection(sectionId) {
  const section = document.getElementById(sectionId).parentElement;
  section.classList.toggle('active');
}

// Function to get CSRF token
function getCSRFToken() {
  // Try multiple methods to get CSRF token
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  if (metaTag) return metaTag.content;
  
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  if (match) return match[1];
  
  if (window.csrf_token) return window.csrf_token;
  
  const csrfInput = document.querySelector('input[name="csrf_token"]');
  if (csrfInput) return csrfInput.value;
  
  console.error('CSRF token not found');
  return null;
}

// Check if current page is admin settings
function isAdminSettingsPage() {
  return document.querySelector('h1')?.textContent === 'Admin Settings';
}

// Initialize all sections as collapsed and load appropriate preferences
document.addEventListener("DOMContentLoaded", () => {
  const sections = document.querySelectorAll('.section');
  sections.forEach(section => {
    section.classList.remove('active');
  });
  
  // Load appropriate preferences based on page
  if (isAdminSettingsPage()) {
    loadAdminPreferences();
    setupAdminCheckboxListeners();
  } else {
    loadUserPreferences();
    setupCheckboxListeners();
  }
  
  // Setup browser notifications checkbox
  setupBrowserNotificationsCheckbox();
  
  // Setup save button event listener
  const saveButton = document.querySelector('.save-button');
  if (saveButton) {
    saveButton.addEventListener('click', () => {
      if (isAdminSettingsPage()) {
        saveAdminSettings();
      } else {
        saveUserPreferences();
      }
    });
  }
});

// ===== USER SETTINGS FUNCTIONS =====

// Load user preferences from backend
async function loadUserPreferences() {
  try {
    const response = await fetch('/api/settings');
    if (response.ok) {
      const preferences = await response.json();
      
      // Update notification preference checkboxes
      document.getElementById('fireHazard').checked = preferences.fireHazard || false;
      document.getElementById('faultyEquipment').checked = preferences.faultyEquipment || false;
      document.getElementById('vandalism').checked = preferences.vandalism || false;
      document.getElementById('suspiciousActivity').checked = preferences.suspiciousActivity || false;
      document.getElementById('otherIncident').checked = preferences.otherIncident || false;
      
      // Update privacy preference checkboxes
      document.getElementById('locationAccess').checked = preferences.locationAccess || false;
      document.getElementById('cameraAccess').checked = preferences.cameraAccess || false;
      document.getElementById('dataSharing').checked = preferences.dataSharing || false;
      
      // Update delivery preference checkboxes
      document.getElementById('emailNotifications').checked = preferences.emailNotifications !== false;
      document.getElementById('smsNotifications').checked = preferences.smsNotifications || false;
      updateBrowserNotificationsCheckbox(preferences.browserNotifications || false);
    } else {
      console.error('Failed to load user preferences:', response.status, response.statusText);
      const errorData = await response.json().catch(() => ({}));
      console.error('Error details:', errorData);
      showNotification('Failed to load settings. Please refresh the page.', 'error');
    }
  } catch (error) {
    console.error('Error loading preferences:', error);
    showNotification('Error loading settings. Please try again.', 'error');
  }
}

// Set up event listeners for checkbox changes (user settings)
function setupCheckboxListeners() {
  const checkboxes = document.querySelectorAll('#notificationPreferences input[type="checkbox"], #privacyPermissions input[type="checkbox"], #notificationDelivery input[type="checkbox"]');
  
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      console.log(`Checkbox ${checkbox.id} changed to ${checkbox.checked}`);
      // Special handling for browser notifications
      if (checkbox.id === 'browserNotifications' && checkbox.checked) {
        requestNotificationPermission();
      }
    });
  });
}

// Save user preferences to backend
async function saveUserPreferences() {
  const saveButton = document.querySelector('.save-button');
  
  // Show loading state
  if (saveButton) {
    saveButton.classList.add('loading');
    saveButton.disabled = true;
  }
  
  const preferences = {
    fireHazard: document.getElementById('fireHazard').checked,
    faultyEquipment: document.getElementById('faultyEquipment').checked,
    vandalism: document.getElementById('vandalism').checked,
    suspiciousActivity: document.getElementById('suspiciousActivity').checked,
    otherIncident: document.getElementById('otherIncident').checked,
    locationAccess: document.getElementById('locationAccess').checked,
    cameraAccess: document.getElementById('cameraAccess').checked,
    dataSharing: document.getElementById('dataSharing').checked,
    emailNotifications: document.getElementById('emailNotifications').checked,
    smsNotifications: document.getElementById('smsNotifications').checked,
    browserNotifications: document.getElementById('browserNotifications').checked
  };
  
  try {
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
      throw new Error('CSRF token not found');
    }
    
    const response = await fetch('/api/settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify(preferences)
    });
    
    if (response.ok) {
      showNotification('Settings saved successfully!', 'success');
      if (saveButton) {
        saveButton.classList.add('success');
        setTimeout(() => saveButton.classList.remove('success'), 2000);
      }
    } else {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData?.error || 'Failed to save settings');
    }
  } catch (error) {
    console.error('Error saving preferences:', error);
    showNotification(error.message, 'error');
    if (saveButton) {
      saveButton.classList.add('error');
      setTimeout(() => saveButton.classList.remove('error'), 2000);
    }
  } finally {
    if (saveButton) {
      saveButton.classList.remove('loading');
      saveButton.disabled = false;
    }
  }
}

// ===== ADMIN SETTINGS FUNCTIONS =====

// Load admin preferences from backend
async function loadAdminPreferences() {
  try {
    const response = await fetch('/api/admin/settings');
    if (response.ok) {
      const preferences = await response.json();
      
      // Update notification checkboxes
      document.getElementById('emailNotifications').checked = preferences.emailNotifications !== false;
      document.getElementById('criticalAlerts').checked = preferences.criticalAlerts !== false;
      document.getElementById('loginAlerts').checked = preferences.loginAlerts !== false;
      document.getElementById('sessionTimeout').checked = preferences.sessionTimeout !== false;
      
      // Update browser notifications
      updateBrowserNotificationsCheckbox(preferences.browserNotifications || false);
      
      // Load profile data if fields exist
      if (document.getElementById('adminName')) {
        document.getElementById('adminName').value = document.getElementById('adminName').dataset.value || '';
      }
      if (document.getElementById('adminEmail')) {
        document.getElementById('adminEmail').value = document.getElementById('adminEmail').dataset.value || '';
      }
    } else {
      console.error('Failed to load admin preferences:', response.status, response.statusText);
      const errorData = await response.json().catch(() => ({}));
      console.error('Error details:', errorData);
      showNotification('Failed to load admin settings. Please refresh the page.', 'error');
    }
  } catch (error) {
    console.error('Error loading admin preferences:', error);
    showNotification('Error loading admin settings. Please try again.', 'error');
  }
}

// Set up event listeners for checkbox changes (admin settings)
function setupAdminCheckboxListeners() {
  const checkboxes = document.querySelectorAll('#notificationSettings input[type="checkbox"], #securitySettings input[type="checkbox"]');
  
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      console.log(`Admin checkbox ${checkbox.id} changed to ${checkbox.checked}`);
      // Special handling for browser notifications
      if (checkbox.id === 'browserNotifications' && checkbox.checked) {
        requestNotificationPermission();
      }
    });
  });
}

// Save admin settings to backend
async function saveAdminSettings() {
  const saveButton = document.querySelector('.save-button');
  
  // Show loading state
  if (saveButton) {
    saveButton.classList.add('loading');
    saveButton.disabled = true;
  }
  
  // Get profile data
  const profileData = {
    username: document.getElementById('adminName').value,
    email: document.getElementById('adminEmail').value
  };
  
  // Get preferences
  const preferences = {
    emailNotifications: document.getElementById('emailNotifications').checked,
    criticalAlerts: document.getElementById('criticalAlerts').checked,
    browserNotifications: document.getElementById('browserNotifications').checked,
    loginAlerts: document.getElementById('loginAlerts').checked,
    sessionTimeout: document.getElementById('sessionTimeout').checked
  };
  
  try {
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
      throw new Error('CSRF token not found');
    }
    
    const headers = {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    };
    
    // First update profile
    const profileResponse = await fetch('/api/admin/update-profile', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(profileData)
    });
    
    if (!profileResponse.ok) {
      const errorData = await profileResponse.json().catch(() => ({}));
      throw new Error(errorData.error || 'Failed to update profile');
    }
    
    // Then update preferences
    const prefsResponse = await fetch('/api/admin/settings', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(preferences)
    });
    
    if (!prefsResponse.ok) {
      const errorData = await prefsResponse.json().catch(() => ({}));
      throw new Error(errorData.error || 'Failed to update preferences');
    }
    
    showNotification('Admin settings saved successfully!', 'success');
    if (saveButton) {
      saveButton.classList.add('success');
      setTimeout(() => saveButton.classList.remove('success'), 2000);
    }
  } catch (error) {
    console.error('Error saving admin settings:', error);
    showNotification(error.message, 'error');
    if (saveButton) {
      saveButton.classList.add('error');
      setTimeout(() => saveButton.classList.remove('error'), 2000);
    }
  } finally {
    if (saveButton) {
      saveButton.classList.remove('loading');
      saveButton.disabled = false;
    }
  }
}

// ===== COMMON FUNCTIONS =====

// Setup browser notifications checkbox with proper state
function setupBrowserNotificationsCheckbox() {
  const browserNotifCheckbox = document.getElementById('browserNotifications');
  if (!browserNotifCheckbox) return;

  if (!('Notification' in window)) {
    browserNotifCheckbox.checked = false;
    browserNotifCheckbox.disabled = true;
    addPermissionWarning(browserNotifCheckbox, 'Browser notifications not supported');
    return;
  }

  if (Notification.permission === 'denied') {
    browserNotifCheckbox.checked = false;
    browserNotifCheckbox.disabled = true;
    addPermissionWarning(browserNotifCheckbox, 'Blocked by browser - check browser settings');
  }
}

// Update browser notifications checkbox state
function updateBrowserNotificationsCheckbox(shouldBeChecked) {
  const browserNotifCheckbox = document.getElementById('browserNotifications');
  if (!browserNotifCheckbox) return;

  if ('Notification' in window) {
    if (Notification.permission === 'granted') {
      browserNotifCheckbox.checked = shouldBeChecked;
      browserNotifCheckbox.disabled = false;
    } else if (Notification.permission === 'denied') {
      browserNotifCheckbox.checked = false;
      browserNotifCheckbox.disabled = true;
      addPermissionWarning(browserNotifCheckbox, 'Blocked by browser - check browser settings');
    } else {
      browserNotifCheckbox.checked = false;
    }
  } else {
    browserNotifCheckbox.checked = false;
    browserNotifCheckbox.disabled = true;
    addPermissionWarning(browserNotifCheckbox, 'Browser notifications not supported');
  }
}

// Add permission warning message
function addPermissionWarning(checkbox, message) {
  const labelGroup = checkbox.closest('.checkbox-container')?.querySelector('.label-group');
  if (!labelGroup) return;

  const existingWarning = labelGroup.querySelector('.permission-warning');
  if (existingWarning) return;

  const warning = document.createElement('small');
  warning.className = 'permission-warning';
  warning.style.color = '#dc3545';
  warning.textContent = message;
  labelGroup.appendChild(warning);
}

// Request browser notification permission
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(permission => {
      const browserNotifCheckbox = document.getElementById('browserNotifications');
      if (!browserNotifCheckbox) return;

      if (permission === 'granted') {
        browserNotifCheckbox.checked = true;
        showNotification('Browser notifications enabled!', 'success');
      } else {
        browserNotifCheckbox.checked = false;
        if (permission === 'denied') {
          browserNotifCheckbox.disabled = true;
          addPermissionWarning(browserNotifCheckbox, 'Blocked by browser - check browser settings');
        }
      }
    });
  }
}

// Enable 2FA (admin only)
function enable2FA() {
  showNotification('Two-factor authentication setup initiated', 'info');
  // Actual 2FA implementation would go here
}

// Change password (admin only)
function changePassword() {
  showNotification('Password change requested', 'info');
  // Actual password change implementation would go here
}

// Show notification to user
function showNotification(message, type = 'info') {
  console.log(`Notification [${type}]: ${message}`);
  
  // Remove existing notifications
  const existingNotifications = document.querySelectorAll('.notification');
  existingNotifications.forEach(notification => {
    notification.remove();
  });
  
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  // Add styles
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background-color: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'};
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 1000;
    font-weight: 500;
    max-width: 350px;
    word-wrap: break-word;
    animation: slideIn 0.3s ease-out;
    display: flex;
    align-items: center;
    gap: 12px;
  `;
  
  // Add icon based on type
  const icon = document.createElement('i');
  icon.className = `fas ${
    type === 'success' ? 'fa-check-circle' : 
    type === 'error' ? 'fa-exclamation-circle' : 
    'fa-info-circle'
  }`;
  notification.prepend(icon);
  
  // Add animation keyframes if not already added
  if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
      .notification {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      }
    `;
    document.head.appendChild(style);
  }
  
  document.body.appendChild(notification);
  
  // Remove notification after 4 seconds
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => {
      if (notification.parentNode) {
        document.body.removeChild(notification);
      }
    }, 300);
  }, 4000);
}

// Debounce function to limit API calls
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Check for new notifications (optional - for real-time updates)
async function checkForNewNotifications() {
  try {
    const endpoint = isAdminSettingsPage() ? '/api/admin/notifications/unread' : '/api/notifications/unread';
    const response = await fetch(endpoint);
    if (response.ok) {
      const notifications = await response.json();
      
      if (notifications.length > 0) {
        updateNotificationBadge(notifications.length);
      }
    }
  } catch (error) {
    console.error('Error checking notifications:', error);
  }
}

// Update notification badge (if you have one in your UI)
function updateNotificationBadge(count) {
  const badge = document.querySelector('.notification-badge');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'block' : 'none';
  }
}

// Poll for new notifications every 30 seconds (optional)
// setInterval(checkForNewNotifications, 30000);