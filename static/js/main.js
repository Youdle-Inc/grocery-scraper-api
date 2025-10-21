// Interactive API Documentation
class APIDocumentation {
    constructor() {
        // Dynamically detect the current host (works for localhost, production domains, etc.)
        this.baseURL = window.location.origin;
        this.init();
    }

    init() {
        this.setupNavigation();
        this.setupCodeTabs();
        this.setupSearch();
        this.setupFormValidation();
        this.setupSyntaxHighlighting();
        this.updateCodeExamples();
    }

    // Navigation
    setupNavigation() {
        const navLinks = document.querySelectorAll('.nav-link');
        const sections = document.querySelectorAll('.content-section');

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                // Remove active class from all links and sections
                navLinks.forEach(l => l.classList.remove('active'));
                sections.forEach(s => s.classList.remove('active'));
                
                // Add active class to clicked link
                link.classList.add('active');
                
                // Show corresponding section
                const targetSection = link.getAttribute('data-section');
                const targetElement = document.getElementById(targetSection);
                if (targetElement) {
                    targetElement.classList.add('active');
                }
            });
        });
    }

    // Code Tab Switching
    setupCodeTabs() {
        const codeTabs = document.querySelectorAll('.code-tab');
        
        codeTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const parent = tab.closest('.code-examples');
                const tabs = parent.querySelectorAll('.code-tab');
                const blocks = parent.querySelectorAll('.code-block');
                
                // Remove active class from all tabs and blocks
                tabs.forEach(t => t.classList.remove('active'));
                blocks.forEach(b => b.classList.remove('active'));
                
                // Add active class to clicked tab
                tab.classList.add('active');
                
                // Show corresponding code block
                const lang = tab.getAttribute('data-lang');
                const block = parent.querySelector(`[data-lang="${lang}"]`);
                if (block) {
                    block.classList.add('active');
                }
            });
        });
    }

    // Search Functionality
    setupSearch() {
        const searchInput = document.getElementById('searchInput');
        const navLinks = document.querySelectorAll('.nav-link');
        
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            
            navLinks.forEach(link => {
                const text = link.textContent.toLowerCase();
                const section = link.getAttribute('data-section');
                
                if (query === '' || text.includes(query) || section.includes(query)) {
                    link.style.display = 'flex';
                } else {
                    link.style.display = 'none';
                }
            });
        });
    }

    // Form Validation
    setupFormValidation() {
        const forms = document.querySelectorAll('.try-it-form');
        
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input[required], select[required]');
            
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateInput(input);
                });
            });
        });
    }

    validateInput(input) {
        const value = input.value.trim();
        const isRequired = input.hasAttribute('required');
        
        if (isRequired && !value) {
            input.style.borderColor = 'var(--error)';
            return false;
        } else {
            input.style.borderColor = 'var(--border)';
            return true;
        }
    }

    // Syntax Highlighting
    setupSyntaxHighlighting() {
        if (typeof hljs !== 'undefined') {
            hljs.highlightAll();
        }
    }

    // Update Code Examples with Current URL
    updateCodeExamples() {
        // Replace all hardcoded localhost URLs with the current origin
        const codeBlocks = document.querySelectorAll('code');
        codeBlocks.forEach(block => {
            if (block.textContent.includes('http://localhost:8000')) {
                block.textContent = block.textContent.replace(/http:\/\/localhost:8000/g, this.baseURL);
            }
        });
        
        // Re-highlight syntax after updating URLs
        if (typeof hljs !== 'undefined') {
            hljs.highlightAll();
        }
    }

    // API Testing Functions
    async testHealth() {
        const startTime = Date.now();
        const responseElement = document.getElementById('health-response');
        const statusElement = document.getElementById('health-status');
        const timeElement = document.getElementById('health-time');
        const bodyElement = document.getElementById('health-response-body');
        
        try {
            const response = await fetch(`${this.baseURL}/health`);
            const endTime = Date.now();
            const responseTime = endTime - startTime;
            
            const data = await response.json();
            
            statusElement.textContent = response.status;
            statusElement.className = response.ok ? 'status-healthy' : 'status-error';
            timeElement.textContent = responseTime;
            bodyElement.textContent = JSON.stringify(data, null, 2);
            
            responseElement.style.display = 'block';
            this.highlightJSON(bodyElement);
            
        } catch (error) {
            statusElement.textContent = 'Error';
            statusElement.className = 'status-error';
            timeElement.textContent = '-';
            bodyElement.textContent = `Error: ${error.message}`;
            responseElement.style.display = 'block';
        }
    }

    async testStores() {
        const zipcode = document.getElementById('stores-zipcode').value;
        const storeChain = document.getElementById('stores-chain').value;
        
        if (!zipcode) {
            alert('Please enter a ZIP code');
            return;
        }
        
        const startTime = Date.now();
        const responseElement = document.getElementById('stores-response');
        const statusElement = document.getElementById('stores-status');
        const timeElement = document.getElementById('stores-time');
        const bodyElement = document.getElementById('stores-response-body');
        
        try {
            let url = `${this.baseURL}/stores/${zipcode}`;
            if (storeChain) {
                url += `?store_chain=${encodeURIComponent(storeChain)}`;
            }
            
            const response = await fetch(url);
            const endTime = Date.now();
            const responseTime = endTime - startTime;
            
            const data = await response.json();
            
            statusElement.textContent = response.status;
            statusElement.className = response.ok ? 'status-healthy' : 'status-error';
            timeElement.textContent = responseTime;
            bodyElement.textContent = JSON.stringify(data, null, 2);
            
            responseElement.style.display = 'block';
            this.highlightJSON(bodyElement);
            
        } catch (error) {
            statusElement.textContent = 'Error';
            statusElement.className = 'status-error';
            timeElement.textContent = '-';
            bodyElement.textContent = `Error: ${error.message}`;
            responseElement.style.display = 'block';
        }
    }

    async testProducts() {
        const query = document.getElementById('products-query').value;
        const storeName = document.getElementById('products-store').value;
        const zipcode = document.getElementById('products-zipcode').value;
        const context = document.getElementById('products-context').value;
        const refresh = document.getElementById('products-refresh').checked;
        
        if (!query) {
            alert('Please enter a search query');
            return;
        }
        
        const startTime = Date.now();
        const responseElement = document.getElementById('products-response');
        const statusElement = document.getElementById('products-status');
        const timeElement = document.getElementById('products-time');
        const bodyElement = document.getElementById('products-response-body');
        
        try {
            const params = new URLSearchParams({
                query: query,
                refresh: refresh
            });
            
            if (storeName) params.append('store_name', storeName);
            if (zipcode) params.append('zipcode', zipcode);
            if (context) params.append('context', context);
            
            const response = await fetch(`${this.baseURL}/products/search?${params}`);
            const endTime = Date.now();
            const responseTime = endTime - startTime;
            
            const data = await response.json();
            
            statusElement.textContent = response.status;
            statusElement.className = response.ok ? 'status-healthy' : 'status-error';
            timeElement.textContent = responseTime;
            bodyElement.textContent = JSON.stringify(data, null, 2);
            
            responseElement.style.display = 'block';
            this.highlightJSON(bodyElement);
            
        } catch (error) {
            statusElement.textContent = 'Error';
            statusElement.className = 'status-error';
            timeElement.textContent = '-';
            bodyElement.textContent = `Error: ${error.message}`;
            responseElement.style.display = 'block';
        }
    }

    async testAggregate() {
        const query = document.getElementById('aggregate-query').value;
        const zipcode = document.getElementById('aggregate-zipcode').value;
        const stores = document.getElementById('aggregate-stores').value;
        const radius = document.getElementById('aggregate-radius').value;
        const refresh = document.getElementById('aggregate-refresh').checked;
        
        if (!query || !zipcode) {
            alert('Please enter both query and ZIP code');
            return;
        }
        
        const startTime = Date.now();
        const responseElement = document.getElementById('aggregate-response');
        const statusElement = document.getElementById('aggregate-status');
        const timeElement = document.getElementById('aggregate-time');
        const bodyElement = document.getElementById('aggregate-response-body');
        
        try {
            const params = new URLSearchParams({
                query: query,
                zipcode: zipcode,
                refresh: refresh
            });
            
            if (stores) params.append('stores', stores);
            if (radius) params.append('radius_miles', radius);
            
            const response = await fetch(`${this.baseURL}/products/aggregate?${params}`);
            const endTime = Date.now();
            const responseTime = endTime - startTime;
            
            const data = await response.json();
            
            statusElement.textContent = response.status;
            statusElement.className = response.ok ? 'status-healthy' : 'status-error';
            timeElement.textContent = responseTime;
            bodyElement.textContent = JSON.stringify(data, null, 2);
            
            responseElement.style.display = 'block';
            this.highlightJSON(bodyElement);
            
        } catch (error) {
            statusElement.textContent = 'Error';
            statusElement.className = 'status-error';
            timeElement.textContent = '-';
            bodyElement.textContent = `Error: ${error.message}`;
            responseElement.style.display = 'block';
        }
    }

    // Utility Functions
    highlightJSON(element) {
        if (typeof hljs !== 'undefined') {
            element.innerHTML = hljs.highlight(element.textContent, { language: 'json' }).value;
        }
    }

    async copyResponse(responseId) {
        const responseElement = document.getElementById(responseId);
        const bodyElement = responseElement.querySelector('.response-body');
        const text = bodyElement.textContent;
        
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Response copied to clipboard!');
        } catch (error) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showToast('Response copied to clipboard!');
        }
    }

    showToast(message) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background-color: var(--success);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 6px;
            z-index: 1000;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // Auto-detect context from query
    detectContext(query) {
        const queryLower = query.toLowerCase();
        
        if (queryLower.includes('cheap') || queryLower.includes('best price') || queryLower.includes('discount')) {
            return 'price_comparison';
        }
        if (queryLower.includes('available') || queryLower.includes('in stock') || queryLower.includes('out of stock')) {
            return 'availability';
        }
        if (queryLower.includes('healthy') || queryLower.includes('nutrition') || queryLower.includes('ingredients')) {
            return 'nutritional';
        }
        if (queryLower.includes('compare brands') || queryLower.includes('brand x vs brand y')) {
            return 'brand_comparison';
        }
        if (queryLower.includes('seasonal') || queryLower.includes('limited edition') || queryLower.includes('holiday')) {
            return 'seasonal';
        }
        
        return '';
    }

    // Update context based on query input
    setupContextDetection() {
        const queryInput = document.getElementById('products-query');
        const contextSelect = document.getElementById('products-context');
        
        if (queryInput && contextSelect) {
            queryInput.addEventListener('input', () => {
                const detectedContext = this.detectContext(queryInput.value);
                if (detectedContext) {
                    contextSelect.value = detectedContext;
                }
            });
        }
    }
}

// Global functions for onclick handlers
function testHealth() {
    api.testHealth();
}

function testStores() {
    api.testStores();
}

function testProducts() {
    api.testProducts();
}

function testAggregate() {
    api.testAggregate();
}

function copyResponse(responseId) {
    api.copyResponse(responseId);
}

// Initialize the API documentation
const api = new APIDocumentation();

// Additional setup after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Setup context detection
    api.setupContextDetection();
    
    // Add loading states to buttons
    const tryButtons = document.querySelectorAll('.try-button');
    tryButtons.forEach(button => {
        button.addEventListener('click', () => {
            button.classList.add('loading');
            setTimeout(() => {
                button.classList.remove('loading');
            }, 2000);
        });
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K for search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            document.getElementById('searchInput').focus();
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('searchInput');
            if (searchInput === document.activeElement) {
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
            }
        }
    });
    
    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIDocumentation;
}
