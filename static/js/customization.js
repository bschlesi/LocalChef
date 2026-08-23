// Toast Helper
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = `toast ${type}`;
    setTimeout(() => {
        toast.className = 'toast hidden';
    }, 4000);
}

// Elements
const customInstructions = document.getElementById('customInstructions');
const mealPrepGroup = document.getElementById('mealPrepToggleGroup');
const macrosGroup = document.getElementById('macrosToggleGroup');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const saveStatus = document.getElementById('saveStatus');

const clearPantryBtn = document.getElementById('clearPantryBtn');
const clearConfirmModal = document.getElementById('clearConfirmModal');
const closeClearModal = document.getElementById('closeClearModal');
const cancelClearModal = document.getElementById('cancelClearModal');
const confirmClearBtn = document.getElementById('confirmClearBtn');

let state = {
    custom_instructions: '',
    meal_prep_mode: false,
    report_macros: false
};

// Toggle helper
function setupToggleGroup(groupElement, onChange) {
    const options = groupElement.querySelectorAll('.toggle-option');
    options.forEach(opt => {
        opt.addEventListener('click', () => {
            options.forEach(o => o.classList.remove('active'));
            opt.classList.add('active');
            const val = opt.getAttribute('data-value') === 'true';
            onChange(val);
        });
    });
}

function setToggleValue(groupElement, val) {
    const options = groupElement.querySelectorAll('.toggle-option');
    options.forEach(opt => {
        const optVal = opt.getAttribute('data-value') === 'true';
        opt.classList.toggle('active', optVal === val);
    });
}

// Load Settings
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        if (data.success) {
            state = data.settings;
            customInstructions.value = state.custom_instructions || '';
            setToggleValue(mealPrepGroup, !!state.meal_prep_mode);
            setToggleValue(macrosGroup, !!state.report_macros);
        } else {
            showToast('Failed to load settings: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (err) {
        showToast('Error connecting to server: ' + err.message, 'error');
    }
}

// Save Settings
async function saveSettings() {
    state.custom_instructions = customInstructions.value.trim();
    saveStatus.textContent = 'Saving...';
    saveStatus.style.color = '#6b7280';

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(state)
        });
        const data = await res.json();
        if (data.success) {
            saveStatus.textContent = 'Changes saved!';
            saveStatus.style.color = '#059669';
            setTimeout(() => {
                saveStatus.textContent = '';
            }, 3000);
        } else {
            saveStatus.textContent = 'Failed to save.';
            saveStatus.style.color = '#dc2626';
            showToast(data.error || 'Could not save settings', 'error');
        }
    } catch (err) {
        saveStatus.textContent = 'Error saving.';
        saveStatus.style.color = '#dc2626';
        showToast('Error: ' + err.message, 'error');
    }
}

// Setup Toggles
setupToggleGroup(mealPrepGroup, (val) => {
    state.meal_prep_mode = val;
});

setupToggleGroup(macrosGroup, (val) => {
    state.report_macros = val;
});

saveSettingsBtn.addEventListener('click', saveSettings);

// Clear Pantry Modal Handlers
clearPantryBtn.addEventListener('click', () => {
    clearConfirmModal.classList.remove('hidden');
});

closeClearModal.addEventListener('click', () => {
    clearConfirmModal.classList.add('hidden');
});

cancelClearModal.addEventListener('click', () => {
    clearConfirmModal.classList.add('hidden');
});

confirmClearBtn.addEventListener('click', async () => {
    try {
        confirmClearBtn.disabled = true;
        confirmClearBtn.textContent = 'Clearing...';

        const res = await fetch('/api/pantry/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            clearConfirmModal.classList.add('hidden');
            showToast('Pantry has been cleared.', 'success');
        } else {
            showToast('Error: ' + (data.error || 'Failed to clear pantry'), 'error');
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
    } finally {
        confirmClearBtn.disabled = false;
        confirmClearBtn.textContent = 'Yes, Clear Pantry';
    }
});

// Initial Load
document.addEventListener('DOMContentLoaded', loadSettings);
