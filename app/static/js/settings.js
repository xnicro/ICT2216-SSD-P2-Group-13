// Function to toggle section visibility with animation
function toggleSection(sectionId) {
  const section = document.getElementById(sectionId).parentElement;
  section.classList.toggle('active');
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
      
      // Update checkboxes based on loaded preferences
      document.getElementById('fireHazard').checked = preferences.fireHazard;
      document.getElementById('faultyEquipment').checked = preferences.faultyEquipment;
      document.getElementById('vandalism').checked = preferences.vandalism;
      document.getElementById('suspiciousActivity').checked = preferences.suspiciousActivity;
      document.getElementById('otherIncident').checked = preferences.otherIncident;
      
      document.getElementById('locationAccess').checked = preferences.locationAccess;
      document.getElementById('cameraAccess').checked = preferences.cameraAccess;
      document.getElementById('dataSharing').checked = preferences.dataSharing;
    } else {
      console.error('Failed to load user preferences');
    }
  } catch (error) {
    console.error('Error loading preferences:', error);
  }
}

// Set up event listeners for checkbox changes
function setupCheckboxListeners() {
  const checkboxes = document.querySelectorAll('input[type="checkbox"]');
  
  checkboxes.forEach(checkbox => {
    checkbox.addEventListener('change', debounce(saveUserPreferences, 500));
  });
}

// Save user preferences to backend
async function saveUserPreferences() {
  const preferences = {
    fireHazard: document.getElementById('fireHazard').checked,
    faultyEquipment: document.getElementById('faultyEquipment').checked,
    vandalism: document.getElementById('vandalism').checked,
    suspiciousActivity: document.getElementById('suspiciousActivity').checked,
    otherIncident: document.getElementById('otherIncident').checked,
    
    locationAccess: document.getElementById('locationAccess').checked,
    cameraAccess: document.getElementById('cameraAccess').checked,
    dataSharing: document.getElementById('dataSharing').checked
  };
  
  try {
    const response = await fetch('/api/settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(preferences)
    });
    
    if (response.ok) {
      showNotification('Settings saved successfully!', 'success');
    } else {
      showNotification('Failed to save settings. Please try again.', 'error');
    }
  } catch (error) {
    console.error('Error saving preferences:', error);
    showNotification('An error occurred while saving settings.', 'error');
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
  // Create notification element
  const notification = document.createElement('div');
  notification.className = `notification ${type}`;
  notification.textContent = message;
  
  // Add styles
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background-color: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : '#2196F3'};
    color: white;
    padding: 16px 24px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 1000;
    font-weight: 500;
    max-width: 300px;
    word-wrap: break-word;
    animation: slideIn 0.3s ease-out;
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
  
  // Remove notification after 3 seconds
  setTimeout(() => {
    notification.style.animation = 'slideOut 0.3s ease-out';
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

// Handle logout
function handleLogout() {
  if (confirm('Are you sure you want to logout?')) {
    window.location.href = '/logout';
  }
}

// Add logout event listener
document.addEventListener('DOMContentLoaded', () => {
  const logoutButton = document.querySelector('.settings-section button');
  if (logoutButton) {
    logoutButton.addEventListener('click', handleLogout);
  }
});

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
setInterval(checkForNewNotifications, 30000);