import re

with open("static/app.js", "r", encoding="utf-8") as f:
    content = f.read()

# 1. showAddServerModal / showEditServerModal
old_show_modals = """    showAddServerModal(show) {
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
    }"""

new_show_modals = """    async showAddServerModal(show) {
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
    }"""
content = content.replace(old_show_modals, new_show_modals)

# 2. setupEventListeners
old_setup = """        addListener('test-webhook-btn', 'click', () => this.handleTestWebhook());"""

new_setup = """        const settingsContainer = document.getElementById('global-webhooks-container');
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
        
        addListener('add-global-webhook-btn', 'click', () => this.addWebhookRow());"""
content = content.replace(old_setup, new_setup)


# 3. loadSettings
old_loadSettings = """    async loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            document.getElementById('settings-webhook').value = data.teams_webhook_url || '';
        } catch (e) {
            console.error(e);
        }
    }"""

new_loadSettings = """    async loadSettings() {
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
    }"""
content = content.replace(old_loadSettings, new_loadSettings)

# 4. handleSaveSettings
old_handleSaveSettings = """    async handleSaveSettings(e) {
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
            });"""

new_handleSaveSettings = """    async handleSaveSettings(e) {
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
            });"""
content = content.replace(old_handleSaveSettings, new_handleSaveSettings)


# 5. handleTestWebhook
old_handleTestWebhook = """    async handleTestWebhook() {
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
            });"""

new_handleTestWebhook = """    async handleTestWebhook(url, btn) {
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
            });"""
content = content.replace(old_handleTestWebhook, new_handleTestWebhook)

# Also fix the final block inside handleTestWebhook
old_testfinal = """        } catch (e) {
            msgDiv.textContent = "Error: " + e.message;
            msgDiv.style.color = "var(--error-color)";
        } finally {
            btn.disabled = false;
        }
    }"""
new_testfinal = """        } catch (e) {
            msgDiv.textContent = "Error: " + e.message;
            msgDiv.style.color = "var(--error-color)";
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }"""
content = content.replace(old_testfinal, new_testfinal)


# 6. startEditDevice
old_startEditDevice = """        document.getElementById('edit-notifications-enabled').checked = device.notifications_enabled !== false;
        document.getElementById('edit-global-notifications-enabled').checked = device.use_global_webhook !== false;
        document.getElementById('edit-server-webhook').value = device.webhook_url || '';

        this.showEditServerModal(true);
    }"""

new_startEditDevice = """        document.getElementById('edit-notifications-enabled').checked = device.notifications_enabled !== false;
        document.getElementById('edit-server-webhook').value = device.webhook_url || '';

        this.showEditServerModal(true).then(() => {
            // override the checkboxes based on device.global_webhooks
            const selected = device.global_webhooks || [];
            this.populateWebhookCheckboxes('edit-global-webhooks-list', selected);
        });
    }"""
content = content.replace(old_startEditDevice, new_startEditDevice)


# 7. handleUpdateServer
old_handleUpdateServer = """        const pingEnabled = document.getElementById('edit-ping-enabled').checked;
        const notificationsEnabled = document.getElementById('edit-notifications-enabled').checked;
        const globalNotificationsEnabled = document.getElementById('edit-global-notifications-enabled').checked;
        const webhookUrl = document.getElementById('edit-server-webhook').value;"""

new_handleUpdateServer = """        const pingEnabled = document.getElementById('edit-ping-enabled').checked;
        const notificationsEnabled = document.getElementById('edit-notifications-enabled').checked;
        const webhookUrl = document.getElementById('edit-server-webhook').value;
        
        const globalWebhooks = Array.from(document.querySelectorAll('#edit-global-webhooks-list .global-webhook-checkbox'))
            .filter(cb => cb.checked)
            .map(cb => cb.value);"""
content = content.replace(old_handleUpdateServer, new_handleUpdateServer)

old_update_payload = """                body: JSON.stringify({
                    new_name: newName,
                    host,
                    ports,
                    ping_enabled: pingEnabled,
                    notifications_enabled: notificationsEnabled,
                    use_global_webhook: globalNotificationsEnabled,
                    webhook_url: webhookUrl ? webhookUrl : null
                })"""

new_update_payload = """                body: JSON.stringify({
                    new_name: newName,
                    host,
                    ports,
                    ping_enabled: pingEnabled,
                    notifications_enabled: notificationsEnabled,
                    global_webhooks: globalWebhooks,
                    webhook_url: webhookUrl ? webhookUrl : null
                })"""
content = content.replace(old_update_payload, new_update_payload)


# 8. handleAddServer
old_handleAddServer = """        const pingEnabled = form.querySelector('#ping-enabled').checked;
        const notificationsEnabled = form.querySelector('#notifications-enabled').checked;
        const globalNotificationsEnabled = form.querySelector('#global-notifications-enabled').checked;
        const webhookUrl = form.querySelector('#server-webhook').value;"""

new_handleAddServer = """        const pingEnabled = form.querySelector('#ping-enabled').checked;
        const notificationsEnabled = form.querySelector('#notifications-enabled').checked;
        const webhookUrl = form.querySelector('#server-webhook').value;
        
        const globalWebhooks = Array.from(form.querySelectorAll('#add-global-webhooks-list .global-webhook-checkbox'))
            .filter(cb => cb.checked)
            .map(cb => cb.value);"""
content = content.replace(old_handleAddServer, new_handleAddServer)

old_add_payload = """                body: JSON.stringify({
                    name,
                    host,
                    ports,
                    webhook_url: webhookUrl ? webhookUrl : null,
                    use_global_webhook: globalNotificationsEnabled,
                    notifications_enabled: notificationsEnabled,
                    ping_enabled: pingEnabled
                })"""

new_add_payload = """                body: JSON.stringify({
                    name,
                    host,
                    ports,
                    webhook_url: webhookUrl ? webhookUrl : null,
                    global_webhooks: globalWebhooks,
                    notifications_enabled: notificationsEnabled,
                    ping_enabled: pingEnabled
                })"""
content = content.replace(old_add_payload, new_add_payload)

with open("static/app.js", "w", encoding="utf-8") as f:
    f.write(content)
