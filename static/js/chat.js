// ── SVG Icon constants (no emojis anywhere) ───────────────────────────────
const ICON = {
    bot: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="13" rx="2"/><path d="M12 8V5"/><circle cx="12" cy="4" r="1.2" fill="currentColor" stroke="none"/><circle cx="9" cy="15" r="1.2" fill="currentColor" stroke="none"/><circle cx="15" cy="15" r="1.2" fill="currentColor" stroke="none"/><path d="M9 19v1M15 19v1"/></svg>`,
    user: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
    volume: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>`,
    volumeMute: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/></svg>`,
    pause: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>`,
    loader: `<svg class="spin-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>`,
};

// ── State ─────────────────────────────────────────────────────────────────
let currentSubject = 'ICT';
let currentMode = 'normal';
let currentClass = 'SSC';
let currentCurriculum = 'NCTB';
let attachedFile = null;
let chatHistory = [];
let _isStreaming = false;

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    updateChips();
    markActive('.subject-item', 'data-subject', currentSubject);
    markActive('.mode-item', 'data-mode', currentMode);

    // Load server history
    if (typeof SERVER_HISTORY !== 'undefined' && SERVER_HISTORY.length > 0) {
        const welcomeMsg = document.getElementById('welcomeMsg');
        if (welcomeMsg) welcomeMsg.style.display = 'none';
        SERVER_HISTORY.forEach(msg => {
            appendMessage(msg.content, msg.role === 'user' ? 'user' : 'bot', false);
            chatHistory.push({ role: msg.role, content: msg.content });
        });
    }

    // Check if voice is available (non-blocking)
    _checkVoiceAvailable();

    // Check Ollama health and show notice if down
    fetch('/api/health').then(r => r.json()).then(data => {
        if (!data.ollama) showNotice('Local AI model (Ollama) is not running. Go to /setup to fix this.');
    }).catch(() => {});
});

function markActive(selector, attr, value) {
    document.querySelectorAll(selector).forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute(attr) === value);
    });
}

// ── Settings ──────────────────────────────────────────────────────────────
function updateSettings() {
    const cl = document.getElementById('classSelect');
    const cur = document.getElementById('curriculumSelect');
    if (cl) currentClass = cl.value;
    if (cur) currentCurriculum = cur.value;
    updateChips();
}

// ── Subject / Mode ────────────────────────────────────────────────────────
function selectSubject(subject) {
    currentSubject = subject;
    markActive('.subject-item', 'data-subject', subject);
    updateChips();
}

function setMode(mode) {
    currentMode = mode;
    markActive('.mode-item', 'data-mode', mode);
    updateChips();
}

function updateChips() {
    const lang = (typeof currentLang !== 'undefined') ? currentLang : 'bn';

    const subjectLabels = {
        'ICT':     { en: 'ICT',     bn: 'আইসিটি' },
        'Bangla':  { en: 'Bangla',  bn: 'বাংলা' },
        'Physics': { en: 'Physics', bn: 'পদার্থ' },
        'English': { en: 'English', bn: 'ইংরেজি' },
    };

    const modeLabels = {
        'normal':       { en: 'Normal',       bn: 'স্বাভাবিক' },
        'simple':       { en: 'Simple',       bn: 'সহজ' },
        'quiz':         { en: 'Quiz',         bn: 'কুইজ' },
        'step-by-step': { en: 'Step-by-Step', bn: 'ধাপে ধাপে' },
    };

    const subChip  = document.getElementById('chipSubject');
    const modeChip = document.getElementById('chipMode');
    const clChip   = document.getElementById('chipClass');
    const curChip  = document.getElementById('chipCurriculum');

    if (subChip)  subChip.textContent  = subjectLabels[currentSubject]?.[lang]  ?? currentSubject;
    if (modeChip) modeChip.textContent = modeLabels[currentMode]?.[lang]        ?? currentMode;
    if (clChip)   clChip.textContent   = currentClass;
    if (curChip)  curChip.textContent  = currentCurriculum;
}

// ── Notice bar ────────────────────────────────────────────────────────────
function showNotice(msg) {
    const bar = document.getElementById('noticeBar');
    if (bar) { bar.textContent = msg; bar.classList.add('visible'); }
}
function hideNotice() {
    const bar = document.getElementById('noticeBar');
    if (bar) bar.classList.remove('visible');
}

// ── Input ─────────────────────────────────────────────────────────────────
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendQuery();
    }
}

// ── File Attachment ───────────────────────────────────────────────────────
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) {
        alert('File too large. Maximum size is 20 MB.');
        event.target.value = '';
        return;
    }
    attachedFile = file;
    document.getElementById('attachmentName').textContent = file.name;
    document.getElementById('attachmentPreview').style.display = 'flex';
    document.getElementById('clipBtn').classList.add('has-file');
}

function removeAttachment() {
    attachedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('attachmentPreview').style.display = 'none';
    document.getElementById('clipBtn').classList.remove('has-file');
}

// ── Chat ──────────────────────────────────────────────────────────────────
function getMessagesArea() {
    return document.getElementById('chatMessages');
}

async function sendQuery() {
    if (_isStreaming) return;

    const inputEl = document.getElementById('queryInput');
    const query = inputEl.value.trim();
    if (!query && !attachedFile) return;

    _isStreaming = true;
    document.getElementById('sendBtn').disabled = true;
    inputEl.value = '';
    autoResize(inputEl);
    hideNotice();

    const welcomeMsg = document.getElementById('welcomeMsg');
    if (welcomeMsg) welcomeMsg.style.display = 'none';

    const displayText = attachedFile
        ? (query ? `[File: ${attachedFile.name}]\n${query}` : `[File: ${attachedFile.name}]`)
        : query;
    appendMessage(displayText, 'user');
    chatHistory.push({ role: 'user', content: query || '(see attached file)' });

    const fileToSend = attachedFile;
    attachedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('attachmentPreview').style.display = 'none';
    document.getElementById('clipBtn').classList.remove('has-file');

    const loadingId = appendLoading();

    try {
        let res;
        if (fileToSend) {
            const fd = new FormData();
            fd.append('file', fileToSend);
            fd.append('messages', JSON.stringify(chatHistory));
            fd.append('subject', currentSubject);
            fd.append('mode', currentMode);
            fd.append('class_level', currentClass);
            fd.append('curriculum', currentCurriculum);
            fd.append('query', query || '');
            res = await fetch('/api/query', { method: 'POST', body: fd });
        } else {
            res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    messages: chatHistory,
                    subject: currentSubject,
                    mode: currentMode,
                    class_level: currentClass,
                    curriculum: currentCurriculum,
                }),
            });
        }

        if (!res.ok) {
            removeMessage(loadingId);
            let errText = 'Server error.';
            try { const d = await res.json(); if (d.error) errText = d.error; } catch (e) {}
            appendMessage(errText, 'bot', true);
            return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let fullReply = '';
        let buffer = '';
        let initialized = false;
        let contentBox = null;
        let msgId = null;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.trim()) continue;
                try {
                    const parsed = JSON.parse(line);

                    if (parsed.status) {
                        const statusEl = document.getElementById(loadingId + '-status');
                        if (statusEl) {
                            const lang = (typeof currentLang !== 'undefined') ? currentLang : 'bn';
                            const map = {
                                'thinking':      { en: 'Thinking…',             bn: 'ভাবছি…' },
                                'retrieving':    { en: 'Looking into your books…', bn: 'বই খুঁজছি…' },
                                'synthesizing':  { en: 'Synthesizing…',          bn: 'তথ্য সাজাচ্ছি…' },
                                'transcribing':  { en: 'Transcribing audio…',    bn: 'অডিও লিখছি…' },
                                'ollama_unavailable': {
                                    en: 'Ollama not running — please restart the app or run setup.',
                                    bn: 'Ollama চালু নেই — সেটআপ করুন।',
                                },
                            };
                            statusEl.textContent = map[parsed.status]?.[lang] || parsed.status;
                        }
                    }

                    if (parsed.chunk || parsed.sources) {
                        if (!initialized) {
                            removeMessage(loadingId);
                            msgId = 'msg-' + Date.now();
                            appendMessage('', 'bot', false, [], msgId);
                            contentBox = document.getElementById(msgId).querySelector('.msg-content');
                            initialized = true;
                        }
                    }

                    if (parsed.chunk) {
                        fullReply += parsed.chunk;
                        if (contentBox) contentBox.textContent = fullReply;
                    }

                    if (parsed.sources && parsed.sources.length > 0 && msgId) {
                        appendSources(document.getElementById(msgId), parsed.sources);
                    }
                } catch (e) {
                    console.error('Stream parse error:', e, line);
                }
            }
            getMessagesArea().scrollTop = getMessagesArea().scrollHeight;
        }

        if (!initialized) removeMessage(loadingId);

        if (fullReply) {
            chatHistory.push({ role: 'assistant', content: fullReply });
        }

    } catch (err) {
        console.error(err);
        removeMessage(loadingId);
        appendMessage('Network error — cannot reach the local server.', 'bot', true);
    } finally {
        _isStreaming = false;
        document.getElementById('sendBtn').disabled = false;
    }
}

function appendMessage(text, sender, isError = false, sources = [], msgId = null) {
    const chatWindow = getMessagesArea();

    const msgDiv = document.createElement('div');
    if (msgId) msgDiv.id = msgId;
    msgDiv.classList.add('msg', sender);

    const avatar = document.createElement('div');
    avatar.classList.add('msg-avatar');
    avatar.innerHTML = sender === 'user' ? ICON.user : ICON.bot;

    const bubble = document.createElement('div');
    bubble.classList.add('msg-bubble');

    const content = document.createElement('div');
    content.classList.add('msg-content');
    content.textContent = text;
    if (isError) content.style.color = 'var(--red)';

    bubble.appendChild(content);

    // TTS button for bot messages (local voice)
    if (sender === 'bot' && !isError) {
        const speechBtn = document.createElement('button');
        speechBtn.classList.add('speech-btn');
        speechBtn.innerHTML = ICON.volume;
        speechBtn.title = 'Play audio';
        speechBtn.onclick = () => playBotAudio(content, speechBtn);
        bubble.appendChild(speechBtn);
    }

    if (sources && sources.length > 0) appendSources(bubble, sources);

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function appendSources(bubbleElement, sources) {
    const bubble = bubbleElement.classList.contains('msg-bubble')
        ? bubbleElement
        : bubbleElement.querySelector('.msg-bubble');
    if (!bubble) return;

    const btn = document.createElement('button');
    btn.classList.add('sources-btn');
    btn.innerHTML = 'Sources &#9660;';
    btn.onclick = () => {
        const div = btn.nextElementSibling;
        const open = div.style.display !== 'none';
        div.style.display = open ? 'none' : 'block';
        btn.innerHTML = open ? 'Sources &#9660;' : 'Sources &#9650;';
    };

    const srcDiv = document.createElement('div');
    srcDiv.style.display = 'none';
    srcDiv.style.marginTop = '10px';
    srcDiv.style.paddingTop = '10px';
    srcDiv.style.borderTop = '1px solid rgba(255,255,255,0.1)';
    srcDiv.style.fontSize = '0.9em';
    srcDiv.style.color = 'var(--text-dim)';
    sources.forEach(src => {
        const p = document.createElement('div');
        p.textContent = `• ${src}`;
        p.style.marginBottom = '4px';
        srcDiv.appendChild(p);
    });

    bubble.appendChild(btn);
    bubble.appendChild(srcDiv);
}

function appendLoading() {
    const id = 'loading-' + Date.now();
    const chatWindow = getMessagesArea();

    const msgDiv = document.createElement('div');
    msgDiv.id = id;
    msgDiv.classList.add('msg', 'bot');

    const avatar = document.createElement('div');
    avatar.classList.add('msg-avatar');
    avatar.innerHTML = ICON.bot;

    const bubble = document.createElement('div');
    bubble.classList.add('msg-bubble');
    bubble.innerHTML = `
        <div class="typing-indicator" style="display:flex;align-items:center;gap:10px;">
            <div class="typing-dots"><span></span><span></span><span></span></div>
            <div id="${id}-status" style="font-size:13.5px;color:var(--text-dim);font-style:italic;">ভাবছি…</div>
        </div>`;

    msgDiv.appendChild(avatar);
    msgDiv.appendChild(bubble);
    chatWindow.appendChild(msgDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return id;
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// ── Local Voice: STT ──────────────────────────────────────────────────────
let _mediaRecorder = null;
let _audioChunks = [];
let _isRecording = false;

async function toggleRecording() {
    const micBtn = document.getElementById('micBtn');

    if (_isRecording && _mediaRecorder) {
        _mediaRecorder.stop();
        return;
    }

    let stream;
    try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
        console.warn('Mic access denied:', err);
        showNotice('Microphone access denied.');
        return;
    }

    _audioChunks = [];
    _mediaRecorder = new MediaRecorder(stream);

    _mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) _audioChunks.push(e.data);
    };

    _mediaRecorder.onstop = async () => {
        _isRecording = false;
        micBtn.classList.remove('recording');
        stream.getTracks().forEach(t => t.stop());

        const blob = new Blob(_audioChunks, { type: 'audio/wav' });
        const fd = new FormData();
        fd.append('audio', blob, 'recording.wav');

        const statusId = appendLoading();
        const statusEl = document.getElementById(statusId + '-status');
        if (statusEl) statusEl.textContent = 'Transcribing…';

        try {
            const res = await fetch('/api/transcribe', { method: 'POST', body: fd });
            const data = await res.json();
            removeMessage(statusId);
            if (data.text) {
                const inputEl = document.getElementById('queryInput');
                inputEl.value = (inputEl.value + ' ' + data.text).trim();
                autoResize(inputEl);
            } else {
                showNotice('Could not transcribe audio.');
            }
        } catch (e) {
            removeMessage(statusId);
            showNotice('STT error: ' + e.message);
        }
    };

    _mediaRecorder.start();
    _isRecording = true;
    micBtn.classList.add('recording');
}

// ── Local Voice: TTS ──────────────────────────────────────────────────────
let _currentAudio = null;

async function playBotAudio(textDiv, btnEl) {
    const text = textDiv.textContent.trim();
    if (!text) return;

    if (_currentAudio) {
        _currentAudio.pause();
        _currentAudio = null;
        document.querySelectorAll('.speech-btn').forEach(b => b.innerHTML = ICON.volume);
        if (btnEl.dataset.playing === 'true') {
            btnEl.dataset.playing = 'false';
            return;
        }
    }

    btnEl.innerHTML = ICON.loader;
    try {
        const res = await fetch('/api/speak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });

        if (!res.ok) { btnEl.innerHTML = ICON.volume; return; }

        const ct = res.headers.get('Content-Type') || '';
        if (!ct.includes('audio')) {
            btnEl.innerHTML = ICON.volumeMute;
            btnEl.title = 'TTS not available';
            return;
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        _currentAudio = new Audio(url);
        _currentAudio.onended = () => {
            btnEl.innerHTML = ICON.volume;
            btnEl.dataset.playing = 'false';
            _currentAudio = null;
        };
        _currentAudio.onerror = () => {
            btnEl.innerHTML = ICON.volume;
            btnEl.dataset.playing = 'false';
            _currentAudio = null;
        };
        btnEl.innerHTML = ICON.pause;
        btnEl.dataset.playing = 'true';
        _currentAudio.play();
    } catch (e) {
        console.error('TTS error:', e);
        btnEl.innerHTML = ICON.volume;
    }
}

// ── Voice availability check ──────────────────────────────────────────────
async function _checkVoiceAvailable() {
    try {
        const res = await fetch('/api/speak', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: '' }),
        });
        const data = await res.json().catch(() => ({}));
        // Show mic button only if microphone is likely to work
        if (!data.error || data.tts_unavailable) {
            // Show mic button — the actual availability check happens on first click
            const micBtn = document.getElementById('micBtn');
            if (micBtn && navigator.mediaDevices) micBtn.style.display = 'flex';
        }
    } catch (e) {
        // Voice check failed silently — mic button stays hidden
    }
}
