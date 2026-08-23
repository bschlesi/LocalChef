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

const chatFeed = document.getElementById('chatFeed');
const promptInput = document.getElementById('promptInput');
const sendBtn = document.getElementById('sendBtn');
const giveRecipeBtn = document.getElementById('giveRecipeBtn');
const goShoppingBtn = document.getElementById('goShoppingBtn');

let isGenerating = false;

function scrollToBottom() {
    chatFeed.scrollTop = chatFeed.scrollHeight;
}

function appendUserBubble(text) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble user-bubble';
    bubble.innerHTML = `<div class="bubble-content">${escapeHtml(text)}</div>`;
    chatFeed.appendChild(bubble);
    scrollToBottom();
}

function createAssistantLoadingBubble() {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble assistant-bubble loading';
    bubble.innerHTML = `
        <div class="bubble-content">
            <div class="loading-dots">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    chatFeed.appendChild(bubble);
    scrollToBottom();
    return bubble;
}

function formatMarkdownToHtml(text) {
    if (!text) return '';
    let escaped = escapeHtml(text);

    // Convert bold **text** or __text__
    escaped = escaped.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    escaped = escaped.replace(/__(.*?)__/g, '<strong>$1</strong>');

    // Convert italic *text* or _text_
    escaped = escaped.replace(/\*(.*?)\*/g, '<em>$1</em>');
    escaped = escaped.replace(/_(.*?)_/g, '<em>$1</em>');

    // Split lines and group into paragraphs or lists
    const lines = escaped.split('\n');
    let html = '';
    let inUl = false;
    let inOl = false;

    for (let line of lines) {
        const trimmed = line.trim();

        // Bullet point
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            if (inOl) { html += '</ol>'; inOl = false; }
            if (!inUl) { html += '<ul>'; inUl = true; }
            html += `<li>${trimmed.substring(2)}</li>`;
        }
        // Numbered list item
        else if (/^\d+\.\s/.test(trimmed)) {
            if (inUl) { html += '</ul>'; inUl = false; }
            if (!inOl) { html += '<ol>'; inOl = true; }
            const itemText = trimmed.replace(/^\d+\.\s/, '');
            html += `<li>${itemText}</li>`;
        }
        // Section headers
        else if (trimmed.startsWith('### ')) {
            if (inUl) { html += '</ul>'; inUl = false; }
            if (inOl) { html += '</ol>'; inOl = false; }
            html += `<h4>${trimmed.substring(4)}</h4>`;
        }
        else if (trimmed.startsWith('## ') || trimmed.startsWith('# ')) {
            if (inUl) { html += '</ul>'; inUl = false; }
            if (inOl) { html += '</ol>'; inOl = false; }
            const headerText = trimmed.replace(/^#+\s/, '');
            html += `<h3>${headerText}</h3>`;
        }
        // Empty line
        else if (trimmed === '') {
            if (inUl) { html += '</ul>'; inUl = false; }
            if (inOl) { html += '</ol>'; inOl = false; }
        }
        // Normal paragraph
        else {
            if (inUl) { html += '</ul>'; inUl = false; }
            if (inOl) { html += '</ol>'; inOl = false; }
            html += `<p>${line}</p>`;
        }
    }

    if (inUl) html += '</ul>';
    if (inOl) html += '</ol>';

    return html;
}

function updateAssistantBubble(bubble, rawContent, isError = false) {
    bubble.classList.remove('loading');
    if (isError) {
        bubble.innerHTML = `
            <div class="bubble-content" style="color: #991b1b;">
                <p><strong>Error:</strong> ${escapeHtml(rawContent)}</p>
                <p><small>Make sure Ollama is running (<code>ollama serve</code>) with model <code>phi4-mini</code>.</small></p>
            </div>
        `;
    } else {
        bubble.innerHTML = `<div class="bubble-content">${formatMarkdownToHtml(rawContent)}</div>`;
    }
    scrollToBottom();
}

// Generate Recipe
async function handleSendPrompt() {
    if (isGenerating) return;
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    promptInput.value = '';
    appendUserBubble(prompt);
    
    isGenerating = true;
    promptInput.disabled = true;
    sendBtn.disabled = true;
    const loadingBubble = createAssistantLoadingBubble();

    try {
        const res = await fetch('/api/recipe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt })
        });
        const data = await res.json();
        if (data.success) {
            updateAssistantBubble(loadingBubble, data.recipe);
        } else {
            updateAssistantBubble(loadingBubble, data.error || 'Failed to generate recipe.', true);
        }
    } catch (err) {
        updateAssistantBubble(loadingBubble, err.message, true);
    } finally {
        isGenerating = false;
        promptInput.disabled = false;
        sendBtn.disabled = false;
        promptInput.focus();
    }
}

// Generate Shopping List
async function handleShoppingList() {
    if (isGenerating) return;

    appendUserBubble("I’m going shopping");
    
    isGenerating = true;
    promptInput.disabled = true;
    sendBtn.disabled = true;
    const loadingBubble = createAssistantLoadingBubble();

    try {
        const res = await fetch('/api/shopping', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        if (data.success) {
            updateAssistantBubble(loadingBubble, data.shopping_list);
        } else {
            updateAssistantBubble(loadingBubble, data.error || 'Failed to generate shopping list.', true);
        }
    } catch (err) {
        updateAssistantBubble(loadingBubble, err.message, true);
    } finally {
        isGenerating = false;
        promptInput.disabled = false;
        sendBtn.disabled = false;
        promptInput.focus();
    }
}

// Event Listeners
sendBtn.addEventListener('click', handleSendPrompt);

promptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        handleSendPrompt();
    }
});

giveRecipeBtn.addEventListener('click', () => {
    promptInput.focus();
    promptInput.setAttribute('placeholder', 'e.g. Chicken Fajitas, Pasta Alfredo, quick stir fry...');
});

goShoppingBtn.addEventListener('click', handleShoppingList);

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
