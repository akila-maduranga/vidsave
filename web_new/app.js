let selectedFormat = null;
let selectedMode = 'direct';
let downloadId = null;
let progressInterval = null;

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
    btnText.innerHTML = '<span class="loader"></span> Checking...';

    try {
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
        } else {
            showError(data.error || 'Failed to fetch formats');
        }
    } catch (err) {
        showError('Connection error');
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Check URL';
    }
}

function displayFormats(formats) {
    const grid = document.getElementById('qualityGrid');
    grid.innerHTML = '';
    
    if (formats.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: rgba(255,255,255,0.6);">No formats available, will use direct download</p>';
        return;
    }

    formats.forEach(format => {
        const btn = document.createElement('button');
        btn.className = 'quality-btn';
        btn.textContent = format.label || format.format_id;
        btn.onclick = () => selectFormat(format.format_id, btn);
        grid.appendChild(btn);
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
                format_id: selectedFormat || 'direct',
                mode: selectedMode,
                filename: filename || null
            })
        });

        const data = await response.json();

        if (response.ok) {
            downloadId = data.download_id;
            document.getElementById('progressSection').classList.remove('hidden');
            document.getElementById('downloadSection').classList.add('hidden');
            document.getElementById('qualitySection').classList.add('hidden');
            document.getElementById('modeSection').classList.add('hidden');
            document.getElementById('filenameSection').classList.add('hidden');
            startProgressPolling();
        } else {
            showError(data.error || 'Failed to start download');
            btn.disabled = false;
            btnText.textContent = 'Start Download';
        }
    } catch (err) {
        showError('Connection error');
        btn.disabled = false;
        btnText.textContent = 'Start Download';
    }
}

function startProgressPolling() {
    progressInterval = setInterval(checkProgress, 1000);
}

async function checkProgress() {
    if (!downloadId) return;

    try {
        const response = await fetch(`/api/progress/${downloadId}`);
        const data = await response.json();

        if (response.ok) {
            updateProgress(data);

            if (data.status === 'complete') {
                clearInterval(progressInterval);
                showDownloadLink();
            } else if (data.status === 'error') {
                clearInterval(progressInterval);
                showError('Download failed: ' + data.action);
            }
        }
    } catch (err) {
        console.error('Progress check failed:', err);
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
    showSuccess('Download complete!');
}

document.getElementById('checkBtn').addEventListener('click', checkUrl);
document.getElementById('urlInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') checkUrl();
});
