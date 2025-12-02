// Settings Page JavaScript

let currentProfile = 'Normal';

async function loadSettings() {
    try {
        const config = await apiGet('/api/config');
        if (config) {
            currentProfile = config.profile_name || 'Normal';
            
            document.getElementById('activeProfile').textContent = currentProfile;
            document.getElementById('gridSpacing').textContent = formatPercent(config.grid_spacing * 100);
            document.getElementById('targetLevels').textContent = config.target_levels;
            
            // Select active profile radio
            const radio = document.getElementById('profile' + currentProfile);
            if (radio) {
                radio.checked = true;
                selectProfile(currentProfile);
            }
        }
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

function selectProfile(profileName) {
    // Remove active class from all options
    document.querySelectorAll('.profile-option').forEach(el => {
        el.classList.remove('active');
    });
    
    // Add active class to selected
    const selectedOption = document.querySelector(`#profile${profileName}`).closest('.profile-option');
    if (selectedOption) {
        selectedOption.classList.add('active');
    }
    
    currentProfile = profileName;
}

async function saveProfile() {
    if (confirm(`Change trading profile to ${currentProfile}? This will recenter the grid.`)) {
        const result = await apiPost(`/api/profile/change?profile=${currentProfile}`);
        if (result && result.status === 'success') {
            showNotification(`Profile changed to ${currentProfile}`, 'success');
            await loadSettings();
        } else {
            showNotification('Failed to change profile', 'error');
        }
    }
}

async function deactivateKillSwitch() {
    if (confirm('Are you sure you want to deactivate the kill-switch? Only do this if it was triggered incorrectly.')) {
        const result = await apiPost('/api/killswitch/deactivate');
        if (result && result.status === 'success') {
            showNotification('Kill-switch deactivated', 'success');
        } else {
            showNotification('Failed to deactivate kill-switch', 'error');
        }
    }
}
