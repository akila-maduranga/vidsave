let selectedFormat = 'best';
let selectedMode = 'direct';
let downloadId = null;
let progressInterval = null;

// Fixed quality options
const QUALITY_OPTIONS = [
    { id: 'best', label: 'Best Quality' },
    { id: '1080p', label: '1080p HD' },
    { id: '720p', label: '720p HD' },
    { id: '480p', label: '480p SD' },
    { id: '360p', label: '360p' }
];

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    document.getElementById('success').classList.add('hidden');
}

function showSuccess(message) {
    const successDiv = document.getElementById('success');
    successDiv.textContent = message;
    successDiv.classList.remove('hidden');
    document.getElementById('error').classList.add('hidden');
}

function hideMessages() {
    document.getElementById('error').classList.add('hidden');
    document.getElementById('success').classList.add('hidden');
}

async function checkUrl() {
    const url = document.getElementById('urlInput').value.trim();
    
    if (!url) {
        showError('Please enter a URL');
        return;
    }

    hideMessages();
    
    const btn = document.getElementById('checkBtn');
    const btnText = document.getElementById('btnText');
    btn.disabled = true;
    btnText.innerHTML = '<span class="loader"></span> Analyzing...';

    try {
        // Simple URL validation - just check if it starts with http/https or has a domain
        if (!url.match(/^(https?:\/\/)?[\w\.-]+\.[a-z]{2,}/i)) {
            showError('Please enter a valid URL');
            btn.disabled = false;
            btnText.textContent = 'Analyze URL';
            return;
        }

        // Call API to extract formats
        const response = await fetch('/api/formats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        const data = await response.json();

        if (response.ok) {
            displayFormats(data.formats || []);
            document.getElementById('modeSection').classList.remove('hidden');
            document.getElementById('filenameSection').classList.remove('hidden');
            document.getElementById('downloadSection').classList.remove('hidden');
            showSuccess('URL analyzed successfully!');
        } else {
            showError(data.error || 'Failed to analyze URL');
        }
    } catch (err) {
        showError('Connection error');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Analyze URL';
    }
}

function displayFormats(formats) {
    const grid = document.getElementById('qualityGrid');
    grid.innerHTML = '';
    
    if (formats.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.6);">No formats available, will use direct download</p>';
        return;
    }

    formats.forEach((format, index) => {
        const btn = document.createElement('button');
        btn.className = 'quality-btn';
        
        // Create label with format info
        const label = document.createElement('span');
        label.textContent = format.label || format.format_id;
        btn.appendChild(label);
        
        // Add height badge if available
        if (format.height && format.height !== 9999) {
            const badge = document.createElement('span');
            badge.style.cssText = 'display: block; font-size: 0.75rem; opacity: 0.7; margin-top: 4px;';
            badge.textContent = `${format.height}p`;
            btn.appendChild(badge);
        }
        
        btn.onclick = () => selectFormat(format.format_id, btn);
        grid.appendChild(btn);
        
        // Auto-select the first format
        if (index === 0) {
            selectFormat(format.format_id, btn);
        }
    });

    document.getElementById('qualitySection').classList.remove('hidden');
}

function selectFormat(formatId, btn) {
    selectedFormat = formatId;
    document.querySelectorAll('.quality-btn').forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
}

function selectMode(mode) {
    selectedMode = mode;
    document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('selected'));
    event.target.classList.add('selected');
}

async function startDownload() {
    const url = document.getElementById('urlInput').value.trim();
    const filename = document.getElementById('filenameInput').value.trim();

    if (!url) {
        showError('Please enter a URL');
        return;
    }

    hideMessages();

    // Reset UI state - hide all previous download-related sections
    document.getElementById('progressSection').classList.add('hidden');
    document.getElementById('downloadCompleteSection').classList.add('hidden');
    document.getElementById('qualitySection').classList.add('hidden');
    document.getElementById('modeSection').classList.add('hidden');
    document.getElementById('filenameSection').classList.add('hidden');

    // Show download section with spinner
    document.getElementById('downloadSection').classList.remove('hidden');
    const btn = document.getElementById('downloadSection').querySelector('button');
    const btnText = document.getElementById('downloadBtnText');
    btn.disabled = true;
    btnText.innerHTML = '<span class="loader"></span> Starting...';

    try {
        const response = await fetch('/api/web-download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                format_id: selectedFormat || 'best',
                mode: selectedMode,
                filename: filename || null
            })
        });

        const data = await response.json();

        if (response.ok) {
            downloadId = data.download_id;
            document.getElementById('progressSection').classList.remove('hidden');
            document.getElementById('downloadSection').classList.add('hidden');
            startProgressPolling();
        } else {
            showError(data.error || 'Failed to start download');
            btn.disabled = false;
            btnText.textContent = 'Download Now';
        }
    } catch (err) {
        showError('Connection error');
        btn.disabled = false;
        btnText.textContent = 'Download Now';
    }
}

function startProgressPolling() {
    // Clear any existing polling first
    if (progressInterval) clearTimeout(progressInterval);
    progressInterval = setTimeout(checkProgress, 1000);
}

async function checkProgress() {
    if (!downloadId) return;

    try {
        const response = await fetch(`/api/progress/${downloadId}`);
        const data = await response.json();

        if (response.ok) {
            updateProgress(data);

            if (data.status === 'complete') {
                showDownloadLink();
                return; // Stop polling
            } else if (data.status === 'error') {
                document.getElementById('progressSection').classList.add('hidden');
                document.getElementById('downloadSection').classList.remove('hidden');
                document.getElementById('downloadSection').querySelector('button').disabled = false;
                document.getElementById('downloadBtnText').textContent = 'Download Now';
                showError('Download failed: ' + (data.action || 'Unknown error'));
                return; // Stop polling
            }
            
            // Continue polling if not complete/error
            progressInterval = setTimeout(checkProgress, 1000);
        } else {
            // Re-poll even on transient HTTP errors
            progressInterval = setTimeout(checkProgress, 2000);
        }
    } catch (err) {
        console.error('Progress check failed:', err);
        // Continue polling despite network errors
        progressInterval = setTimeout(checkProgress, 3000);
    }
}

function updateProgress(data) {
    document.getElementById('progressFill').style.width = data.percentage + '%';
    document.getElementById('progressPercentage').textContent = Math.round(data.percentage) + '%';
    document.getElementById('progressAction').textContent = data.action;
    document.getElementById('progressSpeed').textContent = data.speed;
}

function showDownloadLink() {
    document.getElementById('progressSection').classList.add('hidden');
    const downloadSection = document.getElementById('downloadCompleteSection');
    downloadSection.classList.remove('hidden');
    
    const link = document.getElementById('downloadLink');
    link.href = `/api/download-file/${downloadId}`;
    
    // Fetch file info from progress API
    fetch(`/api/progress/${downloadId}`)
        .then(res => res.json())
        .then(data => {
            if (data.filename) {
                link.textContent = `Download ${data.filename}`;
                if (data.filesize_human) {
                    link.textContent += ` (${data.filesize_human})`;
                }
            }
        })
        .catch(() => {
            link.textContent = 'Download File';
        });
    
    showSuccess('Download complete!');
}

document.getElementById('checkBtn').addEventListener('click', checkUrl);
document.getElementById('urlInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') checkUrl();
});
