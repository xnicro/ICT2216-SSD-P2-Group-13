// Function to toggle section visibility with animation
function toggleSection(sectionId) {
  const section = document.getElementById(sectionId).parentElement;
  section.classList.toggle('active');
}

// Function to get CSRF token
function getCSRFToken() {
  // Try multiple methods to get CSRF token
  // Method 1: From meta tag
  const metaTag = document.querySelector('meta[name="csrf-token"]');
  if (metaTag) return metaTag.content;
  
  // Method 2: From cookie
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  if (match) return match[1];
  
  // Method 3: From window object (if injected by template)
  if (window.csrf_token) return window.csrf_token;
  
  // Method 4: From a hidden input field
  const csrfInput = document.querySelector('input[name="csrf_token"]');
  if (csrfInput) return csrfInput.value;
  
  console.error('CSRF token not found');
  return null;
}

// Initialize all sections as collapsed and load user preferences
document.addEventListener("DOMContentLoaded", () => {
  const sections = document.querySelectorAll('.section');
  sections.forEach(section => {
    section.classList.remove('active');
  });
  
  // Load user preferences from backend
  loadUserPreferences();
  
  // Add event listeners for checkbox changes
  setupCheckboxListeners();
});

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
      document.getElementById('emailNotifications').checked = preferences.emailNotifications !== false; // Default true
      document.getElementById('smsNotifications').checked = preferences.smsNotifications || false;
      document.getElementById('browserNotifications').checked = preferences.browserNotifications || false;
      
    } else {
      console.error('Failed to load user preferences:', response.status, response.statusText);
      const errorData = await response.json().catch(() => ({}));
      console.error('Error details:', errorData);
    }
  } catch (error) {
    console.error('Error loading preferences:', error);
  }
}

// Set up event listeners for checkbox changes
function setupCheckboxListeners() {
  const checkboxes = document.querySelectorAll('input[type="checkbox"]');
  
  checkboxes.forEach(checkbox => {
    // Remove debounce for now to make debugging easier
    checkbox.addEventListener('change', () => {
      console.log(`Checkbox ${checkbox.id} changed to ${checkbox.checked}`);
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
    // Notification preferences
    fireHazard: document.getElementById('fireHazard').checked,
    faultyEquipment: document.getElementById('faultyEquipment').checked,
    vandalism: document.getElementById('vandalism').checked,
    suspiciousActivity: document.getElementById('suspiciousActivity').checked,
    otherIncident: document.getElementById('otherIncident').checked,
    
    // Privacy preferences
    locationAccess: document.getElementById('locationAccess').checked,
    cameraAccess: document.getElementById('cameraAccess').checked,
    dataSharing: document.getElementById('dataSharing').checked,
    
    // Delivery preferences
    emailNotifications: document.getElementById('emailNotifications').checked,
    smsNotifications: document.getElementById('smsNotifications').checked,
    browserNotifications: document.getElementById('browserNotifications').checked
  };
  
  console.log('Saving preferences:', preferences);
  
  try {
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
      throw new Error('CSRF token not found');
    }
    
    const headers = {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    };
    
    console.log('Request headers:', headers);
    
    const response = await fetch('/api/settings', {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(preferences)
    });
    
    console.log('Response status:', response.status);
    
    const responseData = await response.json().catch(() => null);
    console.log('Response data:', responseData);
    
    if (response.ok) {
      showNotification('Settings saved successfully!', 'success');
      if (saveButton) {
        saveButton.classList.add('success');
        setTimeout(() => saveButton.classList.remove('success'), 2000);
      }
    } else {
      const errorMessage = responseData?.error || 'Failed to save settings. Please try again.';
      console.error('Save failed:', errorMessage);
      showNotification(errorMessage, 'error');
      if (saveButton) {
        saveButton.classList.add('error');
        setTimeout(() => saveButton.classList.remove('error'), 2000);
      }
    }
  } catch (error) {
    console.error('Error saving preferences:', error);
    showNotification('An error occurred while saving settings: ' + error.message, 'error');
    if (saveButton) {
      saveButton.classList.add('error');
      setTimeout(() => saveButton.classList.remove('error'), 2000);
    }
  } finally {
    // Remove loading state
    if (saveButton) {
      saveButton.classList.remove('loading');
      saveButton.disabled = false;
    }
  }
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
  
  // Add styles (these will be overridden by CSS classes)
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

// Function to check for new notifications (optional - for real-time updates)
async function checkForNewNotifications() {
  try {
    const response = await fetch('/api/notifications/unread');
    if (response.ok) {
      const notifications = await response.json();
      
      if (notifications.length > 0) {
        // Update notification badge or show alerts
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