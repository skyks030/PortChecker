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

    async showAddServerModal(show) {
        const modal = document.getElementById('add-server-modal');
        if (show) {
            await this.populateWebhookCheckboxes('add-global-webhooks-list');
            modal.classList.add('active');
            modal.classList.remove('hidden');
        } else {
            modal.classList.remove('active');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }
    }

    async showEditServerModal(show) {
        const modal = document.getElementById('edit-server-modal');
        if (show) {
            await this.populateWebhookCheckboxes('edit-global-webhooks-list');
            modal.classList.add('active');
            modal.classList.remove('hidden');
        } else {
            modal.classList.remove('active');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }
    }
    
    async populateWebhookCheckboxes(containerId, selected = []) {
        const container = document.getElementById(containerId);
        if(!container) return;
        
        container.innerHTML = '<span class="loading-indicator"></span> Loading webhooks...';
        
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            const webhooks = data.global_webhooks || [];
            
            container.innerHTML = '';
            if(webhooks.length === 0) {
                container.innerHTML = '<small style="color: var(--text-secondary);">No global webhooks configured in Settings.</small>';
                return;
            }
            
            webhooks.forEach((wh, idx) => {
                const isChecked = selected.includes(wh.alias) || (selected.length === 0 && wh.alias === "Default"); 
                // Default check "Default" if nothing is selected (e.g. adding new)
                
                const html = `
                    <label class="checkbox-container">
                        ${wh.alias}
                        <input type="checkbox" class="global-webhook-checkbox" value="${wh.alias}" ${isChecked ? 'checked' : ''}>
                        <span class="checkmark"></span>
                    </label>
                `;
                container.insertAdjacentHTML('beforeend', html);
            });
        } catch (e) {
            container.innerHTML = '<small style="color: var(--error-color);">Error loading webhooks.</small>';
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

        const settingsContainer = document.getElementById('global-webhooks-container');
        if (settingsContainer) {
            settingsContainer.addEventListener('click', (e) => {
                if (e.target.classList.contains('test-webhook-btn')) {
                    const row = e.target.closest('.webhook-row');
                    const url = row.querySelector('.webhook-url').value;
                    this.handleTestWebhook(url, e.target);
                } else if (e.target.classList.contains('remove-webhook-btn')) {
                    e.target.closest('.webhook-row').remove();
                }
            });
        }
        
        addListener('add-global-webhook-btn', 'click', () => this.addWebhookRow());

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
            const webhooks = data.global_webhooks || [];
            
            const container = document.getElementById('global-webhooks-container');
            container.innerHTML = '';
            
            webhooks.forEach(wh => {
                this.addWebhookRow(wh.alias, wh.url);
            });
            
            if(webhooks.length === 0) {
                this.addWebhookRow();
            }
        } catch (e) {
            console.error(e);
        }
    }
    
    addWebhookRow(alias = '', url = '') {
        const container = document.getElementById('global-webhooks-container');
        const row = document.createElement('div');
        row.className = 'webhook-row';
        row.style.display = 'flex';
        row.style.gap = '10px';
        row.style.alignItems = 'flex-start';
        row.style.backgroundColor = 'var(--bg-tertiary)';
        row.style.padding = '10px';
        row.style.borderRadius = 'var(--border-radius)';
        row.style.position = 'relative';
        
        row.innerHTML = `
            <div style="flex: 1; display: flex; flex-direction: column; gap: 8px;">
                <input type="text" class="webhook-alias" placeholder="Alias (e.g. Default, Alerts)" value="${alias}" required style="padding: 8px;" />
                <input type="url" class="webhook-url" placeholder="https://outlook.office.com/webhook/..." value="${url}" required style="padding: 8px;" />
            </div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <button type="button" class="secondary-btn test-webhook-btn" style="padding: 8px;">Test</button>
                <button type="button" class="secondary-btn remove-webhook-btn" style="padding: 8px; border-color: var(--error-color); color: var(--error-color);">X</button>
            </div>
        `;
        container.appendChild(row);
    }

    async handleSaveSettings(e) {
        e.preventDefault();
        const msgDiv = document.getElementById('settings-message');
        const btn = e.target.querySelector('button[type="submit"]');
        
        const rows = document.querySelectorAll('.webhook-row');
        const globalWebhooks = [];
        
        rows.forEach(row => {
            const alias = row.querySelector('.webhook-alias').value.trim();
            const url = row.querySelector('.webhook-url').value.trim();
            if (alias && url) {
                globalWebhooks.push({ alias, url });
            }
        });

        btn.disabled = true;
        msgDiv.textContent = "Saving...";

        try {
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ global_webhooks: globalWebhooks })
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

    async handleTestWebhook(url, btn) {
        const msgDiv = document.getElementById('settings-message');

        if (!url) {
            msgDiv.textContent = "Please enter a Webhook URL before testing.";
            msgDiv.style.color = "var(--warning-color)";
            return;
        }

        btn.disabled = true;
        let originalText = btn.textContent;
        btn.textContent = "...";
        msgDiv.textContent = "Sending test message...";
        msgDiv.style.color = "var(--text-secondary)";

        try {
            const response = await fetch('/api/settings/test-webhook', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
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
            btn.textContent = originalText;
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
        document.getElementById('edit-server-webhook').value = device.webhook_url || '';

        this.showEditServerModal(true).then(() => {
            // override the checkboxes based on device.global_webhooks
            const selected = device.global_webhooks || [];
            this.populateWebhookCheckboxes('edit-global-webhooks-list', selected);
        });
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
        const webhookUrl = document.getElementById('edit-server-webhook').value;
        
        const globalWebhooks = Array.from(document.querySelectorAll('#edit-global-webhooks-list .global-webhook-checkbox'))
            .filter(cb => cb.checked)
            .map(cb => cb.value);

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
                    global_webhooks: globalWebhooks,
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
        const webhookUrl = form.querySelector('#server-webhook').value;
        
        const globalWebhooks = Array.from(form.querySelectorAll('#add-global-webhooks-list .global-webhook-checkbox'))
            .filter(cb => cb.checked)
            .map(cb => cb.value);

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
                    global_webhooks: globalWebhooks,
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
