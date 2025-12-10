class CustomEndpointCard extends HTMLElement {
    constructor() {
        super();
        this.endpoint = null;
    }

    connectedCallback() {
        const endpointData = this.getAttribute('data-endpoint');
        if (endpointData) {
            this.endpoint = JSON.parse(endpointData);
            this.initialRender();
        }
    }

    static observedAttributes = ['data-endpoint'];

    attributeChangedCallback(name, oldValue, newValue) {
        if (name === 'data-endpoint' && oldValue !== newValue) {
            this.endpoint = JSON.parse(newValue);
            if (this.hasChildNodes()) {
                this.update();
            } else {
                this.initialRender();
            }
        }
    }

    getStatusInfo(endpoint) {
        if (endpoint.last_status === null) {
            return {
                status: 'Pending',
                color: 'yellow',
                icon: 'help-circle',
                bgClass: 'status-pending'
            };
        }

        if (endpoint.is_down || endpoint.last_status !== 200) {
            return {
                status: 'Offline',
                color: 'red',
                icon: 'x-circle',
                bgClass: 'status-offline'
            };
        }
        
        return {
            status: 'Online',
            color: 'green',
            icon: 'check-circle',
            bgClass: 'status-online'
        };
    }

    formatDate(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        return date.toLocaleString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    formatLastNotified(dateString) {
        if (!dateString) return '-- -- --';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    }

    formatUrl(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname + urlObj.pathname;
        } catch {
            return url;
        }
    }

    deleteEndpoint() {
        const event = new CustomEvent('deleteEndpoint', {
            detail: { id: this.endpoint.id }
        });
        document.dispatchEvent(event);
    }

    initialRender() {
        if (!this.endpoint) return;
        
        const statusInfo = this.getStatusInfo(this.endpoint);
        
        this.innerHTML = `
            <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 card-hover fade-in">
                <div class="flex justify-between items-start mb-4">
                    <div class="flex-1 min-w-0">
                        <h3 class="text-sm font-semibold text-gray-800 truncate" title="${this.endpoint.name || this.endpoint.url}">
                            ${this.endpoint.name || this.formatUrl(this.endpoint.url)}
                        </h3>
                        <p class="text-xs text-gray-500 mt-1">
                            ${this.endpoint.name ? `${this.formatUrl(this.endpoint.url)} • ` : ''}ID: ${this.endpoint.id}
                        </p>
                    </div>
                    <button class="text-gray-400 hover:text-red-500 ml-2" onclick="this.closest('custom-endpoint-card').deleteEndpoint()" title="Delete endpoint">
                        <i data-feather="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>

                <div class="flex items-center justify-between mb-3">
                    <span class="status-badge inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border">
                        <i class="status-icon w-3 h-3 mr-1"></i>
                        <span class="status-text"></span>
                    </span>
                    <span class="http-status-text text-xs font-semibold"></span>
                </div>

                <div class="space-y-2 text-xs text-gray-500">
                    <div class="flex justify-between">
                        <span>Last check:</span>
                        <span class="last-checked-text">${this.formatDate(this.endpoint.last_checked)}</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Last notified:</span>
                        <span class="last-notified-text">${this.formatLastNotified(this.endpoint.last_notified)}</span>
                    </div>
                </div>

                <div class="mt-4 pt-3 border-t border-gray-100">
                    <a href="${this.endpoint.url}" target="_blank" class="text-xs text-blue-600 hover:text-blue-800 flex items-center">
                        <i data-feather="external-link" class="w-3 h-3 mr-1"></i>
                        Visit endpoint
                    </a>
                </div>
            </div>
        `;
        this.update();
    }

    update() {
        if (!this.endpoint) return;

        const statusInfo = this.getStatusInfo(this.endpoint);

        // Update status badge
        const statusBadge = this.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.className = `status-badge inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${statusInfo.bgClass}`;
        }
        
        const statusIcon = this.querySelector('.status-icon');
        if (statusIcon) {
            statusIcon.setAttribute('data-feather', statusInfo.icon);
        }

        const statusText = this.querySelector('.status-text');
        if (statusText) {
            statusText.className = `status-text ${
                statusInfo.color === 'green' ? 'text-green-800' :
                statusInfo.color === 'red' ? 'text-red-800' : 'text-yellow-800'
            }`;
            statusText.textContent = statusInfo.status;
        }

        // Update HTTP status
        const httpStatusText = this.querySelector('.http-status-text');
        if (httpStatusText) {
            if (this.endpoint.last_status) {
                httpStatusText.textContent = `HTTP ${this.endpoint.last_status}`;
                httpStatusText.className = `http-status-text text-xs font-semibold ${
                    this.endpoint.last_status === 200 ? 'text-green-600' : 'text-red-600'
                }`;
            } else {
                httpStatusText.textContent = '';
            }
        }

        // Update text content
        const lastChecked = this.querySelector('.last-checked-text');
        if (lastChecked) lastChecked.textContent = this.formatDate(this.endpoint.last_checked);

        const lastNotified = this.querySelector('.last-notified-text');
        if(lastNotified) lastNotified.textContent = this.formatLastNotified(this.endpoint.last_notified);
        
        // Replace feather icons
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

customElements.define('custom-endpoint-card', CustomEndpointCard);