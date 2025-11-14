class CustomNavbar extends HTMLElement {
    connectedCallback() {
        this.innerHTML = `
            <nav class="bg-white shadow-sm border-b border-gray-200">
                <div class="container mx-auto px-4">
                    <div class="flex justify-between items-center h-16">
                        <div class="flex items-center">
                            <div class="flex-shrink-0">
                                <h1 class="text-xl font-bold text-gray-800 flex items-center">
                                    <i data-feather="activity" class="mr-2 text-blue-600"></i>
                                    Endpoint Watchdog
                                </h1>
                            </div>
                        </div>
                        <div class="flex items-center space-x-4">
                            <div class="flex items-center text-sm text-gray-500">
                                <div class="w-2 h-2 bg-green-400 rounded-full mr-2 pulse-animation"></div>
                                Monitoring Active
                            </div>
                            <a href="/docs/" target="_blank" class="text-gray-600 hover:text-blue-600 flex items-center">
                                <i data-feather="book-open" class="mr-1"></i>
                                API Docs
                            </a>
                            <button id="ntfyBtn" class="text-gray-600 hover:text-blue-600 flex items-center">
                               <i data-feather="bell" class="mr-1"></i>
                               Notifications
                           </button>
                        </div>
                    </div>
                </div>
            </nav>
        `;
        
        // Replace feather icons after content is set
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
}

customElements.define('custom-navbar', CustomNavbar);