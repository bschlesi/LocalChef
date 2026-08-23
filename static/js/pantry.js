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
const pantryTableBody = document.getElementById('pantryTableBody');
const selectAllCheckbox = document.getElementById('selectAllCheckbox');
const addBtn = document.getElementById('addBtn');
const removeBtn = document.getElementById('removeBtn');
const importBtn = document.getElementById('importBtn');

// Modals
const addModal = document.getElementById('addModal');
const closeAddModal = document.getElementById('closeAddModal');
const cancelAddModal = document.getElementById('cancelAddModal');
const addItemForm = document.getElementById('addItemForm');

const importModal = document.getElementById('importModal');
const closeImportModal = document.getElementById('closeImportModal');
const cancelImportModal = document.getElementById('cancelImportModal');
const confirmImportBtn = document.getElementById('confirmImportBtn');
const importFilenameInput = document.getElementById('importFilenameInput');

let currentItems = [];

// Load Pantry
async function loadPantry() {
    try {
        const res = await fetch('/api/pantry');
        const data = await res.json();
        if (data.success) {
            currentItems = data.items || [];
            renderPantryTable(currentItems);
        } else {
            showToast('Failed to load pantry: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (err) {
        showToast('Error connecting to server: ' + err.message, 'error');
    }
}

function renderPantryTable(items) {
    if (!items || items.length === 0) {
        pantryTableBody.innerHTML = `
            <tr class="empty-row">
                <td colspan="4">Your pantry is empty. Click "Add items" or "Import CSV" to get started.</td>
            </tr>
        `;
        selectAllCheckbox.checked = false;
        selectAllCheckbox.disabled = true;
        return;
    }

    selectAllCheckbox.disabled = false;
    selectAllCheckbox.checked = false;

    pantryTableBody.innerHTML = items.map((it, idx) => {
        const qtyDisplay = it.units ? `${it.quantity} ${it.units}` : `${it.quantity}`;
        return `
            <tr data-index="${idx}">
                <td class="select-col">
                    <input type="checkbox" class="item-checkbox" data-item="${encodeURIComponent(it.item)}">
                </td>
                <td>${escapeHtml(it.date_added || '')}</td>
                <td>${escapeHtml(it.item || '')}</td>
                <td>${escapeHtml(qtyDisplay)}</td>
            </tr>
        `;
    }).join('');

    // Attach row click / checkbox handlers
    document.querySelectorAll('.item-checkbox').forEach(cb => {
        cb.addEventListener('change', (e) => {
            const row = e.target.closest('tr');
            if (row) row.classList.toggle('selected', e.target.checked);
            updateSelectAllState();
        });
    });
}

function updateSelectAllState() {
    const checkboxes = document.querySelectorAll('.item-checkbox');
    if (checkboxes.length === 0) return;
    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    selectAllCheckbox.checked = checkedCount === checkboxes.length;
    selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
}

selectAllCheckbox.addEventListener('change', () => {
    const isChecked = selectAllCheckbox.checked;
    document.querySelectorAll('.item-checkbox').forEach(cb => {
        cb.checked = isChecked;
        const row = cb.closest('tr');
        if (row) row.classList.toggle('selected', isChecked);
    });
});

// Modal Open/Close helpers
function openModal(modal) {
    modal.classList.remove('hidden');
}

function closeModal(modal) {
    modal.classList.add('hidden');
}

// Add Item
addBtn.addEventListener('click', () => {
    addItemForm.reset();
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('dateInput').value = today;
    openModal(addModal);
});

closeAddModal.addEventListener('click', () => closeModal(addModal));
cancelAddModal.addEventListener('click', () => closeModal(addModal));

addItemForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const item = document.getElementById('itemInput').value.trim();
    const quantity = document.getElementById('qtyInput').value;
    const units = document.getElementById('unitInput').value.trim();
    const dateAdded = document.getElementById('dateInput').value;

    if (!item) {
        showToast('Please enter an item name', 'error');
        return;
    }

    try {
        const res = await fetch('/api/pantry', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                item: item,
                quantity: quantity,
                units: units,
                date_added: dateAdded
            })
        });
        const data = await res.json();
        if (data.success) {
            closeModal(addModal);
            showToast(`Added "${item}" to pantry`, 'success');
            await loadPantry();
        } else {
            showToast('Error: ' + (data.error || 'Could not add item'), 'error');
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
    }
});

// Remove Items
removeBtn.addEventListener('click', async () => {
    const checked = Array.from(document.querySelectorAll('.item-checkbox:checked'));
    if (checked.length === 0) {
        showToast('Please select at least one item to remove', 'info');
        return;
    }

    const itemNames = checked.map(cb => decodeURIComponent(cb.getAttribute('data-item')));
    const confirmMsg = itemNames.length === 1 
        ? `Remove "${itemNames[0]}" from pantry?`
        : `Remove ${itemNames.length} selected items from pantry?`;

    if (!confirm(confirmMsg)) return;

    try {
        const res = await fetch('/api/pantry', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ items: itemNames })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Removed ${itemNames.length} item(s)`, 'success');
            await loadPantry();
        } else {
            showToast('Error: ' + (data.error || 'Could not remove items'), 'error');
        }
    } catch (err) {
        showToast('Error: ' + err.message, 'error');
    }
});

// Import CSV
importBtn.addEventListener('click', () => {
    openModal(importModal);
});

closeImportModal.addEventListener('click', () => closeModal(importModal));
cancelImportModal.addEventListener('click', () => closeModal(importModal));

confirmImportBtn.addEventListener('click', async () => {
    const filename = importFilenameInput.value.trim() || 'pantry_import.csv';
    try {
        confirmImportBtn.disabled = true;
        confirmImportBtn.textContent = 'Importing...';

        const res = await fetch('/api/pantry/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();
        if (data.success) {
            closeModal(importModal);
            showToast(`Successfully imported ${data.result.count} item(s) from ${data.result.filename}`, 'success');
            await loadPantry();
        } else {
            showToast(data.error || 'Import failed', 'error');
        }
    } catch (err) {
        showToast('Import error: ' + err.message, 'error');
    } finally {
        confirmImportBtn.disabled = false;
        confirmImportBtn.textContent = 'Import CSV';
    }
});

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Initial Load
document.addEventListener('DOMContentLoaded', loadPantry);
