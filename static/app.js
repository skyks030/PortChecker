class PortCheckerApp {
    constructor() {
        // Load persistend view or default
        this.currentView = localStorage.getItem('currentView') || 'troubleshoot-view';
        this.troubleshootConfig = [];
        this.isChecking = false;

        this.init();
    }

    async init() {
        // Load troubleshooting options
        await this.loadOptions();
        await this.loadVersion();

        // Setup Event Listeners
        this.setupEventListeners();

        // Restore view
        this.switchView(this.currentView);


        // Initialize WebSocket for background status
        this.initWebSocket();
    }

    async loadVersion() {
        try {
            const res = await fetch('/api/version');
            const data = await res.json();
            const el = document.getElementById('app-version');
            if (el) el.textContent = data.version || '?.?.?';
        } catch (e) {
            console.warn("Failed to load version", e);
        }
    }

    async loadOptions() {
        try {
            const container = document.getElementById('troubleshoot-options');
            const response = await fetch('/api/troubleshoot/options');
            this.troubleshootConfig = await response.json();

            container.innerHTML = '';

            if (this.troubleshootConfig.length === 0) {
                container.innerHTML = '<p class="text-secondary">Keine Hilfe-Optionen konfiguriert.</p>';
                return;
            }

            this.troubleshootConfig.forEach(option => {
                const card = document.createElement('div');
                card.className = 'option-card';
                card.innerHTML = `
                    <div class="option-icon">${option.icon}</div>
                    <div class="option-title">${option.title}</div>
                    <div class="option-desc">${option.description}</div>
                `;

                card.addEventListener('click', () => this.runDiagnostics(option));
                container.appendChild(card);
            });

        } catch (error) {
            console.error('Failed to load options', error);
        }
    }

    async runDiagnostics(option) {
        this.showResultModal(true, option.title);
        const contentDiv = document.getElementById('result-content');

        contentDiv.innerHTML = `
            <div class="scanning-animation">
                <div class="scan-line"></div>
                <p>Analysiere ${option.title}...</p>
                <p class="text-secondary text-sm">Überprüfe ${option.check_tags.join(', ')}...</p>
            </div>
        `;

        try {
            const response = await fetch(`/api/troubleshoot/${option.id}`, { method: 'POST' });
            const data = await response.json();

            this.displayResults(data);

        } catch (error) {
            contentDiv.innerHTML = `
                <div class="check-result-item error">
                    <div class="check-icon-status">⚠️</div>
                    <div class="check-info">
                        <h4>Systemfehler</h4>
                        <div class="check-message">Die Analyse konnte nicht durchgeführt werden.</div>
                    </div>
                </div>
            `;
        }
    }

    displayResults(data) {
        const contentDiv = document.getElementById('result-content');
        contentDiv.innerHTML = '';

        let hasErrors = false;

        // Flatten checks from all devices
        const allChecks = [];
        data.results.devices.forEach(device => {
            if (device.checks) {
                device.checks.forEach(check => {
                    allChecks.push({
                        device: device.name,
                        ...check
                    });
                });
            }
        });

        if (allChecks.length === 0) {
            contentDiv.innerHTML = `
                <div class="scanning-animation">
                    <p>Keine relevanten Checks gefunden.</p>
                </div>
            `;
            return;
        }

        const sortedChecks = allChecks.sort((a, b) => {
            // Errors first
            if (a.status === 'down' && b.status !== 'down') return -1;
            if (a.status !== 'down' && b.status === 'down') return 1;
            return 0;
        });

        sortedChecks.forEach(check => {
            const isError = check.status === 'down';
            if (isError) hasErrors = true;

            const item = document.createElement('div');
            item.className = `check-result-item ${isError ? 'error' : 'success'}`;

            const icon = isError ? '❌' : '✅';
            const statusMsg = isError ? check.error : check.details;

            item.innerHTML = `
                <div class="check-icon-status">${icon}</div>
                <div class="check-info">
                    <h4>${check.device}: ${check.type.toUpperCase()}</h4>
                    <div class="check-message">${statusMsg}</div>
                </div>
            `;

            contentDiv.appendChild(item);
        });

        // Summary Header
        const summary = document.createElement('div');
        summary.style.marginBottom = '1.5rem';
        summary.style.textAlign = 'center';

        if (hasErrors) {
            summary.innerHTML = `<h3 style="color: var(--error-color)">Probleme gefunden</h3><p>Bitte überprüfen Sie die oben genannten Fehler.</p>`;
        } else {
            summary.innerHTML = `<h3 style="color: var(--success-color)">Alles OK</h3><p>Das System scheint einwandfrei zu funktionieren.</p>`;
        }

        contentDiv.insertBefore(summary, contentDiv.firstChild);
    }

    showResultModal(show, title = '') {
        const modal = document.getElementById('diagnostic-result');
        const overlay = document.createElement('div'); // Simple way to block clicks if needed

        if (show) {
            modal.classList.add('active');
            modal.classList.remove('hidden');
            if (title) document.getElementById('result-title').textContent = title;
        } else {
            modal.classList.remove('active');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }
    }

    switchView(viewId) {
        document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
        const activeEl = document.getElementById(viewId);
        if (activeEl) {
            activeEl.classList.add('active');
            this.currentView = viewId;
            localStorage.setItem('currentView', viewId);

            if (viewId === 'status-view') {
                this.renderLegacyStatus();
            }
        }
    }

    setupEventListeners() {
        // Helper to safe-add listener
        const addListener = (id, event, handler) => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener(event, handler);
            } else {
                console.warn(`Element with ID '${id}' not found for event listener.`);
            }
        };

        // Navigation
        addListener('show-status-btn', 'click', () => this.switchView('status-view'));
        addListener('back-to-home-btn', 'click', () => this.switchView('troubleshoot-view'));
        addListener('show-add-server-btn', 'click', () => this.switchView('add-server-view'));
        addListener('back-from-add-btn', 'click', () => this.switchView('status-view'));

        addListener('show-settings-btn', 'click', () => {
            this.loadSettings();
            this.switchView('settings-view');
        });
        addListener('back-from-settings-btn', 'click', () => this.switchView('troubleshoot-view'));
        addListener('back-from-settings-btn', 'click', () => this.switchView('troubleshoot-view'));
        addListener('back-from-edit-btn', 'click', () => this.switchView('status-view'));

        addListener('refresh-btn', 'click', () => this.handleManualRefresh());

        // Modal
        addListener('close-result', 'click', () => this.showResultModal(false));

        // Forms
        const addServerForm = document.getElementById('add-server-form');
        if (addServerForm) {
            addServerForm.addEventListener('submit', (e) => this.handleAddServer(e));
        }

        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => this.handleSaveSettings(e));
        }

        addListener('test-webhook-btn', 'click', () => this.handleTestWebhook());

        const editServerForm = document.getElementById('edit-server-form');
        if (editServerForm) {
            editServerForm.addEventListener('submit', (e) => this.handleUpdateServer(e));
        }

        addListener('delete-server-btn', 'click', () => this.handleDeleteServer());

        // Edit Button Delegate
        const grid = document.getElementById('devices-grid');
        if (grid) {
            grid.addEventListener('click', (e) => {
                const btn = e.target.closest('.edit-device-btn');
                if (btn) {
                    const deviceName = btn.dataset.name;
                    this.startEditDevice(deviceName);
                }
            });
        }
    }

    async loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            document.getElementById('settings-webhook').value = data.teams_webhook_url || '';
        } catch (e) {
            console.error(e);
        }
    }

    async handleSaveSettings(e) {
        e.preventDefault();
        const form = e.target;
        const msgDiv = document.getElementById('settings-message');
        const url = form.querySelector('#settings-webhook').value;
        const btn = form.querySelector('button');

        btn.disabled = true;
        msgDiv.textContent = "Speichere...";

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ teams_webhook_url: url })
            });

            if (response.ok) {
                msgDiv.innerHTML = "✅ Einstellungen gespeichert";
                msgDiv.style.color = "var(--success-color)";
                setTimeout(() => {
                    msgDiv.textContent = "";
                    btn.disabled = false;
                    this.switchView('troubleshoot-view');
                }, 1000);
            } else {
                throw new Error("Fehler beim Speichern");
            }
        } catch (e) {
            msgDiv.style.color = "var(--error-color)";
            btn.disabled = false;
        }
    }

    async handleTestWebhook() {
        const msgDiv = document.getElementById('settings-message');
        const url = document.getElementById('settings-webhook').value;
        const btn = document.getElementById('test-webhook-btn');

        if (!url) {
            msgDiv.textContent = "Bitte eine Webhook URL eingeben vor dem Test.";
            msgDiv.style.color = "var(--warning-color)";
            return;
        }

        btn.disabled = true;
        msgDiv.textContent = "Sende Test-Nachricht...";
        msgDiv.style.color = "var(--text-secondary)";

        try {
            const response = await fetch('/api/settings/test-webhook', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ teams_webhook_url: url })
            });
            const res = await response.json();

            if (response.ok) {
                msgDiv.innerHTML = "✅ " + res.message;
                msgDiv.style.color = "var(--success-color)";
            } else {
                throw new Error(res.detail || "Fehler beim Senden");
            }
        } catch (e) {
            msgDiv.textContent = "Fehler: " + e.message;
            msgDiv.style.color = "var(--error-color)";
        } finally {
            btn.disabled = false;
        }
    }

    startEditDevice(deviceName) {
        const device = this.devicesData.find(d => d.name === deviceName);
        if (!device) return;

        // Find host and port info from checks (heuristic)
        // Find host and port info from checks (heuristic)
        let host = '';
        let ports = '';

        // Try to find host in ping check first, then port check
        const pingCheck = device.checks.find(c => c.type === 'ping');
        if (pingCheck) {
            host = pingCheck.target || '';
        }

        // Gather ports
        const portChecks = device.checks.filter(c => c.type === 'port');
        if (portChecks.length > 0) {
            if (!host) {
                // Determine host from first port check if ping check was missing
                host = portChecks[0].host || '';
            }
            ports = portChecks.map(c => c.port).join(', ');
        }

        document.getElementById('edit-original-name').value = device.name;
        document.getElementById('edit-server-name').value = device.name;
        document.getElementById('edit-server-host').value = host;
        document.getElementById('edit-server-ports').value = ports;
        document.getElementById('edit-notifications-enabled').checked = device.notifications_enabled !== false;

        this.switchView('edit-server-view');
    }

    async handleUpdateServer(e) {
        e.preventDefault();
        const form = e.target;
        const msgDiv = document.getElementById('edit-server-message');
        const btn = form.querySelector('button[type="submit"]');

        const originalName = document.getElementById('edit-original-name').value;
        const newName = document.getElementById('edit-server-name').value;
        const host = document.getElementById('edit-server-host').value;
        const portsStr = document.getElementById('edit-server-ports').value;
        const notificationsEnabled = document.getElementById('edit-notifications-enabled').checked;

        const ports = portsStr.split(',')
            .map(p => parseInt(p.trim()))
            .filter(p => !isNaN(p));

        if (ports.length === 0) {
            msgDiv.textContent = "Bitte mindestens einen gültigen Port angeben.";
            msgDiv.style.color = "var(--error-color)";
            return;
        }

        btn.disabled = true;
        msgDiv.textContent = "Speichere...";

        try {
            const response = await fetch(`/api/devices/${encodeURIComponent(originalName)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    new_name: newName,
                    host,
                    ports,
                    notifications_enabled: notificationsEnabled
                })
            });

            if (response.ok) {
                msgDiv.innerHTML = "✅ Server aktualisiert!";
                msgDiv.style.color = "var(--success-color)";

                // Immediate refresh of local data
                try {
                    const statusRes = await fetch('/api/status');
                    const statusData = await statusRes.json();
                    this.devicesData = statusData.devices;
                    this.updateStats();
                } catch (e) { console.warn("Background refresh failed", e); }

                setTimeout(() => {
                    msgDiv.textContent = "";
                    btn.disabled = false;
                    this.switchView('status-view');
                }, 1000);
            } else {
                const res = await response.json();
                msgDiv.textContent = `Fehler: ${res.detail}`;
                msgDiv.style.color = "var(--error-color)";
                btn.disabled = false;
            }
        } catch (e) {
            msgDiv.textContent = "Verbindungsfehler.";
            msgDiv.style.color = "var(--error-color)";
            btn.disabled = false;
        }
    }

    async handleDeleteServer() {
        const name = document.getElementById('edit-original-name').value;
        if (!confirm(`Möchten Sie den Server "${name}" wirklich löschen?`)) return;

        const msgDiv = document.getElementById('edit-server-message');
        msgDiv.textContent = "Lösche...";

        try {
            const response = await fetch(`/api/devices/${encodeURIComponent(name)}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                msgDiv.innerHTML = "✅ Server gelöscht!";
                msgDiv.style.color = "var(--success-color)";

                // Immediate refresh of local data
                try {
                    const statusRes = await fetch('/api/status');
                    const statusData = await statusRes.json();
                    this.devicesData = statusData.devices;
                    this.updateStats();
                } catch (e) { console.warn("Background refresh failed", e); }

                setTimeout(() => {
                    msgDiv.textContent = "";
                    this.switchView('status-view');
                }, 1000);
            } else {
                const res = await response.json();
                msgDiv.textContent = `Fehler: ${res.detail}`;
                msgDiv.style.color = "var(--error-color)";
            }
        } catch (e) {
            console.error(e);
            msgDiv.textContent = "Verbindungsfehler.";
            msgDiv.style.color = "var(--error-color)";
        }
    }

    async handleAddServer(e) {
        e.preventDefault();

        const form = e.target;
        const msgDiv = document.getElementById('add-server-message');
        const submitBtn = form.querySelector('button[type="submit"]');

        // Data gathering
        const name = form.querySelector('#server-name').value;
        const host = form.querySelector('#server-host').value;
        const portsStr = form.querySelector('#server-ports').value;
        const notificationsEnabled = form.querySelector('#notifications-enabled').checked;
        // Old logic used webhookUrl, now we just pass boolean logic via params or updated logic
        // But backend expects AddDeviceRequest. We can hijack webhook_url param or just rely on backend defaulting.
        // Wait, I updated backend to accept notifications_enabled but AddDeviceRequest still has webhook_url.
        // Actually I added notifications_enabled to AddDeviceRequest.
        // So I should send it.

        // specific parsing
        const ports = portsStr.split(',')
            .map(p => parseInt(p.trim()))
            .filter(p => !isNaN(p));

        if (ports.length === 0) {
            msgDiv.textContent = "Bitte mindestens einen gültigen Port angeben.";
            msgDiv.style.color = "var(--error-color)";
            return;
        }

        submitBtn.disabled = true;
        msgDiv.textContent = "Server wird hinzugefügt...";
        msgDiv.style.color = "var(--text-secondary)";

        try {
            const response = await fetch('/api/devices', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    host,
                    ports,
                    webhook_url: null, // Deprecated in frontend
                    notifications_enabled: notificationsEnabled
                })
            });

            const result = await response.json();

            if (response.ok) {
                msgDiv.innerHTML = `✅ Server erfolgreich hinzugefügt!`;
                msgDiv.style.color = "var(--success-color)";
                form.reset();

                // Immediate refresh of local data
                try {
                    const statusRes = await fetch('/api/status');
                    const statusData = await statusRes.json();
                    this.devicesData = statusData.devices;
                    this.updateStats();
                } catch (e) { console.warn("Background refresh failed", e); }

                // Nach kurzer Zeit zurück zur Status-Ansicht
                setTimeout(() => {
                    msgDiv.textContent = "";
                    submitBtn.disabled = false;
                    this.switchView('status-view');
                }, 1500);
            } else {
                msgDiv.textContent = `Fehler: ${result.detail || "Unbekannter Fehler"}`;
                msgDiv.style.color = "var(--error-color)";
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error(error);
            msgDiv.textContent = "Verbindungsfehler beim Hinzufügen.";
            msgDiv.style.color = "var(--error-color)";
            submitBtn.disabled = false;
        }
    }

    // --- Legacy WebSocket Handling for Status View ---

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.type === 'checking_started') {
                this.setLoadingState(true);
            } else if (data.type === 'status_update' || data.type === 'initial_status') {
                this.devicesData = data.devices;
                this.setLoadingState(false);

                if (this.currentView === 'status-view') {
                    this.renderLegacyStatus();
                }
                this.updateStats();
            }
        };

        this.ws.onclose = () => setTimeout(() => this.initWebSocket(), 3000);
    }

    setLoadingState(isLoading) {
        this.isChecking = isLoading;
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.disabled = isLoading;
            refreshBtn.classList.toggle('rotating', isLoading); // Add simple rotation class if desired, or relying on visual disabled state
        }

        // Update cards if they exist
        if (this.currentView === 'status-view' && this.devicesData) {
            this.renderLegacyStatus(); // Re-render to show/hide spinners
        }
    }

    async handleManualRefresh() {
        if (this.isChecking) return;
        this.setLoadingState(true);
        try {
            await fetch('/api/test', { method: 'POST' });
        } catch (e) {
            console.error("Manual refresh failed", e);
            this.setLoadingState(false);
        }
    }

    renderLegacyStatus() {
        if (!this.devicesData) return;

        const grid = document.getElementById('devices-grid');
        grid.innerHTML = '';

        this.devicesData.forEach(device => {
            // Simplified card for legacy view
            const card = document.createElement('div');
            card.className = `stat-card ${this.isChecking ? 'loading' : ''}`; // Reuse style
            card.style.textAlign = 'left';
            card.style.borderLeft = `4px solid ${device.status === 'up' ? 'var(--success-color)' : 'var(--error-color)'}`;
            card.style.position = 'relative';

            const statusIcon = device.status === 'up' ? '🟢' : '🔴';

            card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3>
                        <span class="loading-indicator"></span>
                        ${statusIcon} ${device.name}
                    </h3>
                    <button class="icon-btn edit-device-btn" data-name="${device.name}" title="Bearbeiten" style="font-size:1.2rem;">✏️</button>
                </div>
                <div style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary);">
                    ${device.checks.map(c =>
                `<div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span>${c.type}</span>
                            <span style="color: ${c.status === 'up' ? 'var(--success-color)' : 'var(--error-color)'}">${c.status === 'up' ? 'OK' : 'ERR'}</span>
                         </div>`
            ).join('')}
                </div>
            `;
            grid.appendChild(card);
        });
    }

    updateStats() {
        if (!this.devicesData) return;
        const total = this.devicesData.length;
        const up = this.devicesData.filter(d => d.status === 'up').length;
        const down = total - up;

        document.getElementById('total-devices').textContent = total;
        document.getElementById('devices-up').textContent = up;
        document.getElementById('devices-down').textContent = down;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.app = new PortCheckerApp();
});
