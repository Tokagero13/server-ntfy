// API Configuration
const API_BASE = '/api/endpoints';

// Application state
let endpoints = [];
let filteredEndpoints = [];
let isLoading = false;
let endpointsSearchQuery = '';

// DOM elements
let addEndpointBtn;
let addEndpointModal;
let closeModalBtn;
let cancelBtn;
let endpointForm;
let endpointUrl;
let endpointName;
let endpointsContainer;
let ntfyBtn;
let ntfyModal;
let closeNtfyModalBtn;
let logEndpointFilter;
let logSortOrder;
let logPagination;
let endpointsSearchInput;
let logSearchInput;
let logStatusFilter;
let logRefreshBtn;

// Log state
let logState = {
    currentPage: 1,
    perPage: 25,
    sortBy: 'timestamp',
    order: 'desc',
    endpointFilter: '',
    statusFilter: '',
    searchQuery: '',
    totalPages: 1
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeElements();
    initializeEventListeners();
    loadEndpoints();
   loadNotificationLogs();
    
    // Auto-refresh every 10 seconds
    setInterval(loadEndpoints, 10000);
   setInterval(loadNotificationLogs, 15000);
});

function initializeElements() {
    addEndpointBtn = document.getElementById('addEndpointBtn');
    addEndpointModal = document.getElementById('addEndpointModal');
    closeModalBtn = document.getElementById('closeModalBtn');
    cancelBtn = document.getElementById('cancelBtn');
    endpointForm = document.getElementById('endpointForm');
    endpointUrl = document.getElementById('endpointUrl');
    endpointName = document.getElementById('endpointName');
    endpointsContainer = document.getElementById('endpointsContainer');
   ntfyBtn = document.getElementById('ntfyBtn');
   ntfyModal = document.getElementById('ntfyModal');
   closeNtfyModalBtn = document.getElementById('closeNtfyModalBtn');
   logEndpointFilter = document.getElementById('logEndpointFilter');
   logStatusFilter = document.getElementById('logStatusFilter');
   logSortOrder = document.getElementById('logSortOrder');
   logPagination = document.getElementById('logPagination');
   endpointsSearchInput = document.getElementById('endpointsSearchInput');
   logSearchInput = document.getElementById('logSearchInput');
   logRefreshBtn = document.getElementById('logRefreshBtn');
}

function initializeEventListeners() {
   // Modal controls
   addEndpointBtn.addEventListener('click', showModal);
    closeModalBtn.addEventListener('click', hideModal);
    cancelBtn.addEventListener('click', hideModal);
   ntfyBtn.addEventListener('click', showNtfyModal);
   closeNtfyModalBtn.addEventListener('click', hideNtfyModal);
    
    // Form submission
    endpointForm.addEventListener('submit', handleSubmit);
    
    // Close modal on outside click
    addEndpointModal.addEventListener('click', function(e) {
        if (e.target === addEndpointModal) {
            hideModal();
        }
    });

   ntfyModal.addEventListener('click', function(e) {
       if (e.target === ntfyModal) {
           hideNtfyModal();
       }
   });
    
    // Listen for delete endpoint events
    document.addEventListener('deleteEndpoint', function(e) {
        deleteEndpoint(e.detail.id);
    });
    
    // ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !addEndpointModal.classList.contains('hidden')) {
            hideModal();
        }
       if (e.key === 'Escape' && !ntfyModal.classList.contains('hidden')) {
           hideNtfyModal();
       }
   });

   // Log controls
   if (logEndpointFilter) {
       logEndpointFilter.addEventListener('change', handleLogEndpointFilter);
   }
   if (logStatusFilter) {
       logStatusFilter.addEventListener('change', handleLogStatusFilter);
   }
   if (logSearchInput) {
       logSearchInput.addEventListener('input', debounce(handleLogSearch, 500));
   }
   if (logRefreshBtn) {
       logRefreshBtn.addEventListener('click', handleLogRefresh);
   }
   logSortOrder.addEventListener('click', handleLogSortOrder);

   // Endpoints search
   if (endpointsSearchInput) {
       endpointsSearchInput.addEventListener('input', debounce(handleEndpointsSearch, 300));
   }
}

function showNtfyModal() {
   ntfyModal.classList.remove('hidden');
}

function hideNtfyModal() {
   ntfyModal.classList.add('hidden');
}

function showModal() {
    addEndpointModal.classList.remove('hidden');
    endpointUrl.focus();
}

function hideModal() {
    addEndpointModal.classList.add('hidden');
    endpointForm.reset();
}

async function loadEndpoints() {
    if (isLoading) return;

    try {
        isLoading = true;

        const response = await fetch(`${API_BASE}/`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const newEndpoints = await response.json();
        
        // On first load with data, clear any potential "no endpoints" message.
        if (endpoints.length === 0 && newEndpoints.length > 0) {
            endpointsContainer.innerHTML = '';
        }

        endpoints = newEndpoints;
        filterEndpoints();
        renderEndpoints();
        updateStats();
        updateLogEndpointFilter();
        
    } catch (error) {
        console.error('Error loading endpoints:', error);
        // Show full error state only if there are no endpoints currently displayed
        if (endpoints.length === 0) {
            showErrorState('Failed to load endpoints. Please make sure the server is running.');
        }
    } finally {
        isLoading = false;
    }
}

function showLoadingState() {
    endpointsContainer.innerHTML = `
        <div class="col-span-full flex items-center justify-center py-12">
            <div class="text-center">
                <div class="spinner mx-auto mb-4"></div>
                <p class="text-gray-500">Loading endpoints...</p>
            </div>
        </div>
    `;
}

function showErrorState(message) {
    endpointsContainer.innerHTML = `
        <div class="col-span-full">
            <div class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                <i data-feather="alert-circle" class="mx-auto mb-2 text-red-500"></i>
                <p class="text-red-700">${message}</p>
                <button onclick="loadEndpoints()" class="mt-3 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm">
                    Retry
                </button>
            </div>
        </div>
    `;
    feather.replace();
}

function renderEndpoints() {
    const endpointsToRender = filteredEndpoints.length > 0 || endpointsSearchQuery ? filteredEndpoints : endpoints;
    
    if (endpointsToRender.length === 0 && endpoints.length === 0 && endpointsContainer.innerHTML.includes('spinner')) {
        endpointsContainer.innerHTML = `
            <div class="col-span-full">
                <div class="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-12 text-center">
                    <i data-feather="server" class="mx-auto mb-4 text-gray-400" style="width: 48px; height: 48px;"></i>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">No endpoints monitored</h3>
                    <p class="text-gray-500 mb-4">Get started by adding your first endpoint to monitor.</p>
                    <button onclick="showModal()" class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">
                        Add Endpoint
                    </button>
                </div>
            </div>
        `;
        feather.replace();
        return;
    }

    if (endpointsToRender.length === 0 && endpointsSearchQuery) {
        endpointsContainer.innerHTML = `
            <div class="col-span-full">
                <div class="bg-yellow-50 border-2 border-dashed border-yellow-300 rounded-lg p-12 text-center">
                    <i data-feather="search" class="mx-auto mb-4 text-yellow-400" style="width: 48px; height: 48px;"></i>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">No endpoints found</h3>
                    <p class="text-gray-500 mb-4">Try adjusting your search query.</p>
                </div>
            </div>
        `;
        feather.replace();
        return;
    }

    const endpointIdsOnPage = new Set([...endpointsContainer.children].map(el => el.dataset.endpointId));
    const newEndpointIds = new Set(endpointsToRender.map(e => String(e.id)));

    // 1. Update existing and add new
    endpointsToRender.forEach(endpoint => {
        const existingCard = endpointsContainer.querySelector(`[data-endpoint-id='${endpoint.id}']`);
        if (existingCard) {
            // Update existing card
            existingCard.dataset.endpoint = JSON.stringify(endpoint);
            // The web component will handle its own internal updates
        } else {
            // Add new card
            const card = document.createElement('custom-endpoint-card');
            card.dataset.endpointId = endpoint.id;
            card.dataset.endpoint = JSON.stringify(endpoint);
            endpointsContainer.appendChild(card);
        }
    });

    // 2. Remove old
    endpointIdsOnPage.forEach(id => {
        if (!newEndpointIds.has(id)) {
            const cardToRemove = endpointsContainer.querySelector(`[data-endpoint-id='${id}']`);
            if (cardToRemove) {
                cardToRemove.remove();
            }
        }
    });
}

function filterEndpoints() {
    if (!endpointsSearchQuery) {
        filteredEndpoints = [];
        return;
    }
    
    const query = endpointsSearchQuery.toLowerCase();
    filteredEndpoints = endpoints.filter(endpoint => {
        return endpoint.url.toLowerCase().includes(query) ||
               (endpoint.name && endpoint.name.toLowerCase().includes(query)) ||
               (endpoint.id && endpoint.id.toString().includes(query));
    });
}

function handleEndpointsSearch(event) {
    endpointsSearchQuery = event.target.value.toLowerCase().trim();
    filterEndpoints();
    renderEndpoints();
}

function updateStats() {
    const stats = {
        total: endpoints.length,
        online: endpoints.filter(e => e.last_status === 200).length,
        offline: endpoints.filter(e => e.is_down).length,
        pending: endpoints.filter(e => e.last_status === null).length
    };

    // Dispatch event for status cards to update
    const event = new CustomEvent('statsUpdated', { detail: stats });
    document.dispatchEvent(event);
}

async function handleSubmit(e) {
    e.preventDefault();
    
    const url = endpointUrl.value.trim();
    if (!url) {
        showNotification('Please enter a domain or URL', 'error');
        return;
    }
    
    // Basic client-side validation
    if (!isValidDomainOrUrl(url)) {
        showNotification('Please enter a valid domain (e.g., example.com) or URL', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url })
        });
        
        if (response.ok) {
            hideModal();
            showNotification('Endpoint added successfully!', 'success');
            loadEndpoints();
        } else {
            const error = await response.json();
            showNotification(error.message || 'Failed to add endpoint', 'error');
        }
    } catch (error) {
        console.error('Error adding endpoint:', error);
        showNotification('Failed to add endpoint', 'error');
    }
}

function isValidDomainOrUrl(input) {
    // Remove whitespace
    input = input.trim();
    
    // Check if it's already a URL
    if (input.startsWith('http://') || input.startsWith('https://')) {
        try {
            new URL(input);
            return true;
        } catch {
            return false;
        }
    }
    
    // Check for IP address with optional port (IPv4)
    const ipv4WithPortRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?::[1-9][0-9]{0,4})?$/;
    if (ipv4WithPortRegex.test(input)) {
        return true;
    }
    
    // Check for localhost variations
    if (/^localhost(?::[1-9][0-9]{0,4})?$/.test(input)) {
        return true;
    }
    
    // Check for any domain (including single level domains and local domains)
    // More permissive regex that allows:
    // - Single level domains (e.g., "server", "api")
    // - Multi-level domains (e.g., "api.example.com")
    // - Domains with numbers, hyphens
    // - Local domains (e.g., "server.local", "api.internal")
    // - Domains with ports
    const domainWithPortRegex = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?))*(?::[1-9][0-9]{0,4})?$/;
    
    return domainWithPortRegex.test(input);
}

async function deleteEndpoint(id) {
    if (!confirm('Are you sure you want to delete this endpoint?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/${id}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showNotification('Endpoint deleted successfully!', 'success');
            loadEndpoints();
        } else {
            showNotification('Failed to delete endpoint', 'error');
        }
    } catch (error) {
        console.error('Error deleting endpoint:', error);
        showNotification('Failed to delete endpoint', 'error');
    }
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    
    notification.innerHTML = `
        <div class="flex items-center">
            <i data-feather="${
                type === 'success' ? 'check' :
                type === 'error' ? 'x' :
                'info'
            }" class="mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    feather.replace();
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export for global use
async function loadNotificationLogs() {
    try {
        const { currentPage, perPage, sortBy, order, endpointFilter, statusFilter, searchQuery } = logState;
        const url = new URL('/api/endpoints/notifications', window.location.origin);
        url.searchParams.append('page', currentPage);
        url.searchParams.append('per_page', perPage);
        url.searchParams.append('sort_by', sortBy);
        url.searchParams.append('order', order);
        if (endpointFilter) {
            url.searchParams.append('endpoint_filter', endpointFilter);
        }
        if (statusFilter) {
            url.searchParams.append('status_filter', statusFilter);
        }
        if (searchQuery) {
            url.searchParams.append('search', searchQuery);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        logState.totalPages = data.total_pages;
        renderNotificationLogs(data.logs, data.total_items);
        renderPagination(data);
    } catch (error) {
        console.error('Error loading notification logs:', error);
        const container = document.getElementById('notificationLogsContainer');
        container.innerHTML = `<tr><td colspan="4" class="text-center text-red-500 py-4">Failed to load logs.</td></tr>`;
    }
}

function renderNotificationLogs(logs, totalItems) {
    const container = document.getElementById('notificationLogsContainer');
    if (!container) return;

    if (logs.length === 0) {
        container.innerHTML = `
            <tr>
                <td colspan="4" class="px-6 py-8 text-center">
                    <div class="text-gray-400 mb-2">
                        <i data-feather="inbox" class="mx-auto" style="width: 48px; height: 48px;"></i>
                    </div>
                    <p class="text-sm text-gray-500">No notification logs found.</p>
                    ${logState.searchQuery || logState.endpointFilter || logState.statusFilter ?
                        '<p class="text-xs text-gray-400 mt-1">Try adjusting your filters.</p>' : ''}
                </td>
            </tr>
        `;
        feather.replace();
        return;
    }

    container.innerHTML = logs.map((log, index) => `
        <tr class="hover:bg-gray-50 transition-colors">
            <td class="px-6 py-4 text-sm text-gray-900">
                <div class="font-medium truncate max-w-xs" title="${escapeHtml(log.endpoint_url)}">${escapeHtml(log.endpoint_url)}</div>
            </td>
            <td class="px-6 py-4 text-sm text-gray-600">
                <div class="max-w-md truncate" title="${escapeHtml(log.message)}">${escapeHtml(log.message)}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
                <span class="px-2.5 py-1 inline-flex items-center text-xs leading-5 font-semibold rounded-full ${
                    log.status === 'sent' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }">
                    <i data-feather="${log.status === 'sent' ? 'check' : 'x'}" class="w-3 h-3 mr-1"></i>
                    ${log.status}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${formatTimestamp(log.timestamp)}
            </td>
        </tr>
    `).join('');

    feather.replace();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function renderPagination({ total_pages, current_page, total_items }) {
    if (!logPagination) return;

    if (total_pages <= 1) {
        logPagination.innerHTML = total_items > 0 ?
            `<div class="text-center text-sm text-gray-500">Showing ${total_items} log${total_items !== 1 ? 's' : ''}</div>` : '';
        return;
    }

    const maxButtons = 7;
    let startPage = Math.max(1, current_page - Math.floor(maxButtons / 2));
    let endPage = Math.min(total_pages, startPage + maxButtons - 1);

    if (endPage - startPage < maxButtons - 1) {
        startPage = Math.max(1, endPage - maxButtons + 1);
    }

    let buttons = '<div class="flex items-center justify-between">';
    buttons += '<div class="text-sm text-gray-500">';
    buttons += `Showing page ${current_page} of ${total_pages} (${total_items} total)`;
    buttons += '</div>';
    buttons += '<div class="flex items-center space-x-1">';

    // Previous button
    if (current_page > 1) {
        buttons += `<button onclick="changeLogPage(${current_page - 1})" class="px-3 py-1.5 border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 transition-colors">
            <i data-feather="chevron-left" class="w-4 h-4"></i>
        </button>`;
    }

    // First page
    if (startPage > 1) {
        buttons += `<button onclick="changeLogPage(1)" class="px-3 py-1.5 border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 transition-colors">1</button>`;
        if (startPage > 2) {
            buttons += '<span class="px-2 text-gray-400">...</span>';
        }
    }

    // Page numbers
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === current_page;
        const classes = isActive
            ? 'px-3 py-1.5 border border-blue-600 rounded-md bg-blue-600 text-white font-medium'
            : 'px-3 py-1.5 border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 transition-colors';
        buttons += `<button onclick="changeLogPage(${i})" class="${classes}">${i}</button>`;
    }

    // Last page
    if (endPage < total_pages) {
        if (endPage < total_pages - 1) {
            buttons += '<span class="px-2 text-gray-400">...</span>';
        }
        buttons += `<button onclick="changeLogPage(${total_pages})" class="px-3 py-1.5 border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 transition-colors">${total_pages}</button>`;
    }

    // Next button
    if (current_page < total_pages) {
        buttons += `<button onclick="changeLogPage(${current_page + 1})" class="px-3 py-1.5 border border-gray-300 rounded-md bg-white text-gray-700 hover:bg-gray-50 transition-colors">
            <i data-feather="chevron-right" class="w-4 h-4"></i>
        </button>`;
    }

    buttons += '</div></div>';
    logPagination.innerHTML = buttons;
    feather.replace();
}

function changeLogPage(page) {
    logState.currentPage = page;
    loadNotificationLogs();
}

function handleLogEndpointFilter(event) {
    logState.endpointFilter = event.target.value;
    logState.currentPage = 1; // Reset to first page
    loadNotificationLogs();
}

function handleLogStatusFilter(event) {
    logState.statusFilter = event.target.value;
    logState.currentPage = 1; // Reset to first page
    loadNotificationLogs();
}

function handleLogSearch(event) {
    logState.searchQuery = event.target.value.trim();
    logState.currentPage = 1; // Reset to first page
    loadNotificationLogs();
}

function handleLogRefresh() {
    loadNotificationLogs();
    showNotification('Logs refreshed', 'success');
}

function handleLogSortOrder() {
    logState.order = logState.order === 'desc' ? 'asc' : 'desc';
    const iconName = logState.order === 'desc' ? 'arrow-down' : 'arrow-up';
    logSortOrder.innerHTML = feather.icons[iconName].toSvg();
    loadNotificationLogs();
}

function updateLogEndpointFilter() {
    if (!logEndpointFilter) return;
    
    // Сохранить текущий выбор
    const currentValue = logEndpointFilter.value;
    
    // Очистить и заполнить новыми опциями
    logEndpointFilter.innerHTML = '<option value="">All Endpoints</option>';
    
    // Создать уникальный список endpoint URL
    const uniqueEndpoints = [...new Set(endpoints.map(e => e.url))];
    uniqueEndpoints.forEach(url => {
        const endpoint = endpoints.find(e => e.url === url);
        const displayName = endpoint.name || url;
        const option = document.createElement('option');
        option.value = url;
        option.textContent = displayName;
        logEndpointFilter.appendChild(option);
    });
    
    // Восстановить выбор если он все еще доступен
    if (uniqueEndpoints.includes(currentValue)) {
        logEndpointFilter.value = currentValue;
    } else {
        logState.endpointFilter = '';
        logEndpointFilter.value = '';
    }
}


window.showModal = showModal;
window.loadEndpoints = loadEndpoints;
window.changeLogPage = changeLogPage;