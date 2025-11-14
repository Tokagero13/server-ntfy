class CustomStatusCard extends HTMLElement {
    constructor() {
        super();
        this.stats = {
            total: 0,
            online: 0,
            offline: 0,
            pending: 0
        };
    }

    connectedCallback() {
        this.initialRender();
        document.addEventListener('statsUpdated', (event) => {
            this.update(event.detail);
        });
    }

    update(stats) {
        if (!stats) return;

        // Only update if data has changed
        if (JSON.stringify(this.stats) === JSON.stringify(stats)) {
            return;
        }
        
        this.stats = stats;

        const totalEl = this.querySelector('.stat-total');
        if (totalEl) totalEl.textContent = this.stats.total;

        const onlineEl = this.querySelector('.stat-online');
        if (onlineEl) onlineEl.textContent = this.stats.online;

        const issuesEl = this.querySelector('.stat-issues');
        if (issuesEl) issuesEl.textContent = this.stats.offline;
        
        const offlineEl = this.querySelector('.stat-offline-detail');
        if (offlineEl) offlineEl.textContent = `${this.stats.offline} offline`;

        // Обновляем весь блок для pending кнопки
        const cardElement = this.querySelector('.status-card-item:last-child .text-sm');
        if (cardElement) {
            cardElement.innerHTML = `
                <span class="stat-offline-detail text-red-600">${this.stats.offline} offline</span>
                ${this.stats.pending > 0 ? `<div class="mt-2"><button onclick="showModal()" class="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full hover:bg-yellow-200">+ ${this.stats.pending} Pending</button></div>` : ''}
            `;
        }
    }

    initialRender() {
        this.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 status-card-item">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold text-gray-800">Total Endpoints</h3>
                    <i data-feather="server" class="text-blue-600"></i>
                </div>
                <div class="stat-total text-3xl font-bold text-gray-900 mb-2">${this.stats.total}</div>
                <div class="text-sm text-gray-500">Monitored services</div>
            </div>

            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 status-card-item">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold text-green-600">Online</h3>
                    <i data-feather="check-circle" class="text-green-600"></i>
                </div>
                <div class="stat-online text-3xl font-bold text-green-600 mb-2">${this.stats.online}</div>
                <div class="text-sm text-gray-500">Services running</div>
            </div>

            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 status-card-item">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-semibold text-red-600">Issues</h3>
                    <i data-feather="alert-circle" class="text-red-600"></i>
                </div>
                <div class="stat-issues text-3xl font-bold text-red-600 mb-2">${this.stats.offline}</div>
                <div class="text-sm text-gray-500">
                    <span class="stat-offline-detail text-red-600">${this.stats.offline} offline</span>
                    ${this.stats.pending > 0 ? `<div class="mt-2"><button onclick="showModal()" class="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded-full hover:bg-yellow-200">+ ${this.stats.pending} Pending</button></div>` : ''}
                </div>
            </div>
        </div>
        `;

        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

customElements.define('custom-status-card', CustomStatusCard);