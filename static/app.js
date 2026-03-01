class PortCheckerApp {
    constructor() {
        // Load persistend view or default
        this.currentView = localStorage.getItem('currentView') || 'status-view';
        this.isChecking = false;

        this.init();
    }

    async init() {
        await this.loadVersion();

        // Setup Event Listeners
        this.setupEventListeners();

        // Restore view
        if (this.currentView !== 'status-view' && this.currentView !== 'settings-view') {
            this.currentView = 'status-view';
        }
        this.switchView(this.currentView);

        // Initialize WebSocket for background status
        this.initWebSocket();
    }

    async loadVersion() {
        try {
            const res = await fetch('/api/version');
            const data = await res.json();
            const el = document.getElementById('app-version');
            if (el) el.textContent = 'v' + (data.version || '?.?.?');
        } catch (e) {
            console.warn("Failed to load version", e);
        }
    }

    showSettingsModal(show) {
        const modal = document.getElementById('settings-modal');
        if (show) {
            this.loadSettings();
            modal.classList.add('active');
            modal.classList.remove('hidden');
        } else {
            modal.classList.remove('active');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }
    }

    showAddServerModal(show) {
        const modal = document.getElementById('add-server-modal');
        if (show) {
            modal.classList.add('active');
            modal.classList.remove('hidden');
        } else {
            modal.classList.remove('active');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }
    }

    showEditServerModal(show) {
        const modal = document.getElementById('edit-server-modal');
        if (show) {
            modal.classList.add('active');
            modal.classList.remove('hidden');
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
        addListener('show-add-server-btn', 'click', () => this.showAddServerModal(true));
        addListener('close-add-server-btn', 'click', () => this.showAddServerModal(false));
        addListener('close-edit-server-btn', 'click', () => this.showEditServerModal(false));
        addListener('refresh-btn', 'click', () => this.handleManualRefresh());

        // Modals
        addListener('show-settings-btn', 'click', () => this.showSettingsModal(true));
        addListener('close-settings-btn', 'click', () => this.showSettingsModal(false));


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
                msgDiv.innerHTML = "✅ Settings saved";
                msgDiv.style.color = "var(--success-color)";
                setTimeout(() => {
                    msgDiv.textContent = "";
                    btn.disabled = false;
                    this.showSettingsModal(false);
                }, 1000);
            } else {
                throw new Error("Error saving settings");
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
            msgDiv.textContent = "Please enter a Webhook URL before testing.";
            msgDiv.style.color = "var(--warning-color)";
            return;
        }

        btn.disabled = true;
        msgDiv.textContent = "Sending test message...";
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
                throw new Error(res.detail || "Error sending message");
            }
        } catch (e) {
            msgDiv.textContent = "Error: " + e.message;
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
        document.getElementById('edit-ping-enabled').checked = !!pingCheck;
        document.getElementById('edit-notifications-enabled').checked = device.notifications_enabled !== false;
        document.getElementById('edit-global-notifications-enabled').checked = device.use_global_webhook !== false;
        document.getElementById('edit-server-webhook').value = device.webhook_url || '';

        this.showEditServerModal(true);
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
        const pingEnabled = document.getElementById('edit-ping-enabled').checked;
        const notificationsEnabled = document.getElementById('edit-notifications-enabled').checked;
        const globalNotificationsEnabled = document.getElementById('edit-global-notifications-enabled').checked;
        const webhookUrl = document.getElementById('edit-server-webhook').value;

        const ports = portsStr.split(',')
            .map(p => parseInt(p.trim()))
            .filter(p => !isNaN(p));

        if (ports.length === 0) {
            msgDiv.textContent = "Please specify at least one valid port.";
            msgDiv.style.color = "var(--error-color)";
            return;
        }

        btn.disabled = true;
        msgDiv.textContent = "Saving...";

        try {
            const response = await fetch(`/api/devices/${encodeURIComponent(originalName)}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    new_name: newName,
                    host,
                    ports,
                    ping_enabled: pingEnabled,
                    notifications_enabled: notificationsEnabled,
                    use_global_webhook: globalNotificationsEnabled,
                    webhook_url: webhookUrl ? webhookUrl : null
                })
            });

            if (response.ok) {
                msgDiv.innerHTML = "✅ Server updated!";
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
                    this.showEditServerModal(false);
                }, 1000);
            } else {
                const res = await response.json();
                msgDiv.textContent = `Error: ${res.detail}`;
                msgDiv.style.color = "var(--error-color)";
                btn.disabled = false;
            }
        } catch (e) {
            msgDiv.textContent = "Connection error.";
            msgDiv.style.color = "var(--error-color)";
            btn.disabled = false;
        }
    }

    async handleDeleteServer() {
        const name = document.getElementById('edit-original-name').value;
        if (!confirm(`Do you really want to delete the server "${name}"?`)) return;

        const msgDiv = document.getElementById('edit-server-message');
        msgDiv.textContent = "Deleting...";

        try {
            const response = await fetch(`/api/devices/${encodeURIComponent(name)}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                msgDiv.innerHTML = "✅ Server deleted!";
                msgDiv.style.color = "var(--success-color)";

                // Immediate refresh of local data
                try {
                    const statusRes = await fetch('/api/status');
                    const statusData = await res.json();
                    this.devicesData = statusData.devices;
                    this.updateStats();
                } catch (e) { console.warn("Background refresh failed", e); }

                setTimeout(() => {
                    msgDiv.textContent = "";
                    this.showEditServerModal(false);
                }, 1000);
            } else {
                const res = await response.json();
                msgDiv.textContent = `Error: ${res.detail}`;
                msgDiv.style.color = "var(--error-color)";
            }
        } catch (e) {
            console.error(e);
            msgDiv.textContent = "Connection error.";
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
        const pingEnabled = form.querySelector('#ping-enabled').checked;
        const notificationsEnabled = form.querySelector('#notifications-enabled').checked;
        const globalNotificationsEnabled = form.querySelector('#global-notifications-enabled').checked;
        const webhookUrl = form.querySelector('#server-webhook').value;

        // specific parsing
        const ports = portsStr.split(',')
            .map(p => parseInt(p.trim()))
            .filter(p => !isNaN(p));

        if (ports.length === 0) {
            msgDiv.textContent = "Please specify at least one valid port.";
            msgDiv.style.color = "var(--error-color)";
            return;
        }

        submitBtn.disabled = true;
        msgDiv.textContent = "Adding server...";
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
                    webhook_url: webhookUrl ? webhookUrl : null,
                    use_global_webhook: globalNotificationsEnabled,
                    notifications_enabled: notificationsEnabled,
                    ping_enabled: pingEnabled
                })
            });

            const result = await response.json();

            if (response.ok) {
                msgDiv.innerHTML = `✅ Server successfully added!`;
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
                    this.showAddServerModal(false);
                }, 1500);
            } else {
                msgDiv.textContent = `Error: ${result.detail || "Unknown error"}`;
                msgDiv.style.color = "var(--error-color)";
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error(error);
            msgDiv.textContent = "Connection error while adding.";
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
                    <button class="icon-btn edit-device-btn" data-name="${device.name}" title="Edit" style="font-size:1.2rem;">⚙️</button>
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
