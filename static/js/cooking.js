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
const stopBtn = document.getElementById('stopBtn');
const giveRecipeBtn = document.getElementById('giveRecipeBtn');
const goShoppingBtn = document.getElementById('goShoppingBtn');

let isGenerating = false;
let currentAbortController = null;

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
            <div class="gen-status">Connecting to Ollama…</div>
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

function formatElapsed(seconds) {
    if (seconds == null) return '';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
}

function wordCount(text) {
    const t = text.trim();
    return t ? t.split(/\s+/).length : 0;
}

function renderStreamingBubble(bubble, statusHtml, accumulatedText) {
    bubble.querySelector('.bubble-content').innerHTML =
        `<div class="gen-status">${statusHtml}</div>` + formatMarkdownToHtml(accumulatedText);
    scrollToBottom();
}

function setStopVisible(visible) {
    if (!stopBtn) return;
    stopBtn.style.display = visible ? 'flex' : 'none';
    sendBtn.style.display = visible ? 'none' : 'flex';
}

// Parses a fetch() ReadableStream of `data: {...}\n\n` frames (SSE-style,
// hand-rolled since EventSource doesn't support POST bodies) and invokes
// onEvent for each parsed JSON payload as it arrives.
async function streamSSE(url, body, { signal, onEvent }) {
    const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal,
    });

    if (!res.ok) {
        let errMsg = `Request failed (${res.status})`;
        try {
            const errJson = await res.json();
            if (errJson && errJson.error) errMsg = errJson.error;
        } catch (_) { /* response wasn't JSON, keep default message */ }
        throw new Error(errMsg);
    }
    if (!res.body) {
        throw new Error('This browser does not support streaming responses.');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sepIndex;
        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, sepIndex);
            buffer = buffer.slice(sepIndex + 2);
            const dataLine = rawEvent.split('\n').find(line => line.startsWith('data: '));
            if (!dataLine) continue;
            try {
                onEvent(JSON.parse(dataLine.slice(6)));
            } catch (e) {
                console.error('Failed to parse stream event:', dataLine, e);
            }
        }
    }
}

// Drives a streamed generation (recipe or shopping list) against a loading
// bubble, updating it live as events arrive.
async function runStreamedGeneration(url, body, userBubbleText) {
    if (isGenerating) return;
    if (userBubbleText) appendUserBubble(userBubbleText);

    isGenerating = true;
    promptInput.disabled = true;
    setStopVisible(true);

    const loadingBubble = createAssistantLoadingBubble();
    let accumulated = '';
    let sawFirstToken = false;
    let lastRenderAt = 0;
    const RENDER_THROTTLE_MS = 120;

    currentAbortController = new AbortController();

    try {
        await streamSSE(url, body, {
            signal: currentAbortController.signal,
            onEvent: (event) => {
                switch (event.type) {
                    case 'status':
                        renderStreamingBubble(loadingBubble, `⏳ ${escapeHtml(event.message)}`, accumulated);
                        break;

                    case 'heartbeat':
                        renderStreamingBubble(
                            loadingBubble,
                            `⏳ Still working… ${formatElapsed(event.elapsed)} elapsed`,
                            accumulated
                        );
                        break;

                    case 'stalled':
                        renderStreamingBubble(
                            loadingBubble,
                            `⚠️ ${escapeHtml(event.message)} (${formatElapsed(event.elapsed)} elapsed)`,
                            accumulated
                        );
                        break;

                    case 'chunk': {
                        if (!sawFirstToken) {
                            sawFirstToken = true;
                            loadingBubble.classList.remove('loading');
                        }
                        accumulated += event.content;
                        const now = performance.now();
                        if (now - lastRenderAt > RENDER_THROTTLE_MS) {
                            lastRenderAt = now;
                            renderStreamingBubble(
                                loadingBubble,
                                `✍️ Generating… ${formatElapsed(event.elapsed)} · ~${wordCount(accumulated)} words so far`,
                                accumulated
                            );
                        }
                        break;
                    }

                    case 'done': {
                        const speed = event.tokens_per_sec ? ` · ${event.tokens_per_sec} tok/s` : '';
                        const statsLine = event.tokens
                            ? `Done in ${formatElapsed(event.elapsed)} · ${event.tokens} tokens${speed}`
                            : `Done in ${formatElapsed(event.elapsed)}`;
                        loadingBubble.classList.remove('loading');
                        renderStreamingBubble(loadingBubble, `✅ ${statsLine}`, accumulated);
                        break;
                    }

                    case 'error':
                        updateAssistantBubble(loadingBubble, event.message || 'Something went wrong.', true);
                        break;

                    default:
                        // Unknown event type — ignore rather than break the stream.
                        break;
                }
            },
        });
    } catch (err) {
        if (err.name === 'AbortError') {
            updateAssistantBubble(
                loadingBubble,
                accumulated
                    ? `Stopped. Partial response is shown above:\n\n${accumulated}`
                    : 'Generation stopped before any text arrived.',
                !accumulated
            );
            if (accumulated) {
                renderStreamingBubble(loadingBubble, '🛑 Stopped by user', accumulated);
            }
        } else {
            updateAssistantBubble(loadingBubble, err.message, true);
        }
    } finally {
        isGenerating = false;
        promptInput.disabled = false;
        setStopVisible(false);
        currentAbortController = null;
        promptInput.focus();
    }
}

async function handleSendPrompt() {
    if (isGenerating) return;
    const prompt = promptInput.value.trim();
    if (!prompt) return;
    promptInput.value = '';
    await runStreamedGeneration('/api/recipe', { prompt }, prompt);
}

async function handleShoppingList() {
    if (isGenerating) return;
    await runStreamedGeneration('/api/shopping', {}, "I’m going shopping");
}

function handleStopGeneration() {
    if (currentAbortController) {
        currentAbortController.abort();
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

if (stopBtn) {
    stopBtn.addEventListener('click', handleStopGeneration);
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
