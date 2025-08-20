/* ScriptFlow - Main Application JavaScript */

// Global variables
let autoRefreshInterval = null;
let refreshIndicator = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
    initializeAutoRefresh();
    initializeDeleteModals();
    initializePythonSettings();
    initializeTerminal();
    initializeExecutionDetail();
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Auto-refresh functionality for logs page
function initializeAutoRefresh() {
    // Only run on logs page
    if (!window.location.pathname.includes('/logs')) return;
    
    const runningExecutions = document.querySelectorAll('.badge:contains("🔄")');
    
    if (runningExecutions.length > 0) {
        startAutoRefresh();
    }
}

function startAutoRefresh() {
    // Show toast notification
    showToast('Auto-refresh enabled', 'Page will refresh every 10 seconds while scripts are running', 'info');
    
    // Create refresh indicator
    createRefreshIndicator();
    
    // Start interval
    autoRefreshInterval = setInterval(function() {
        const runningExecutions = document.querySelectorAll('.rotating');
        
        if (runningExecutions.length > 0) {
            showRefreshIndicator();
            
            // Refresh page after showing indicator
            setTimeout(function() {
                window.location.reload();
            }, 1000);
        } else {
            stopAutoRefresh();
        }
    }, 10000); // 10 seconds
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        hideRefreshIndicator();
        showToast('Auto-refresh stopped', 'No running scripts detected', 'info');
    }
}

function createRefreshIndicator() {
    if (refreshIndicator) return;
    
    refreshIndicator = document.createElement('div');
    refreshIndicator.className = 'refresh-indicator';
    refreshIndicator.innerHTML = '<i class="bi bi-arrow-clockwise rotating me-2"></i>Auto-refreshing...';
    refreshIndicator.style.display = 'none';
    document.body.appendChild(refreshIndicator);
}

function showRefreshIndicator() {
    if (refreshIndicator) {
        refreshIndicator.style.display = 'block';
        refreshIndicator.classList.add('show');
        
        setTimeout(function() {
            hideRefreshIndicator();
        }, 2000);
    }
}

function hideRefreshIndicator() {
    if (refreshIndicator) {
        refreshIndicator.classList.remove('show');
        refreshIndicator.classList.add('hide');
        
        setTimeout(function() {
            refreshIndicator.style.display = 'none';
            refreshIndicator.classList.remove('hide');
        }, 300);
    }
}

// Toast notification system
function showToast(title, message, type = 'info') {
    const toastContainer = getOrCreateToastContainer();
    
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = 'toast align-items-center text-white bg-' + (type === 'info' ? 'primary' : type);
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong><br>
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function getOrCreateToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.zIndex = '1055';
        document.body.appendChild(container);
    }
    return container;
}

// Delete confirmation modal
function initializeDeleteModals() {
    // Handle delete buttons
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn-delete') || e.target.closest('.btn-delete')) {
            e.preventDefault();
            const btn = e.target.matches('.btn-delete') ? e.target : e.target.closest('.btn-delete');
            const scriptName = btn.dataset.scriptName;
            const scriptId = btn.dataset.scriptId;
            showDeleteModal(scriptName, scriptId);
        }
    });
}

function showDeleteModal(scriptName, scriptId) {
    // Update modal content
    document.getElementById('deleteScriptName').textContent = scriptName;
    
    // Set up confirm button
    const confirmBtn = document.getElementById('confirmDelete');
    confirmBtn.onclick = function() {
        deleteScript(scriptId);
    };
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

function deleteScript(scriptId) {
    const confirmBtn = document.getElementById('confirmDelete');
    const originalText = confirmBtn.innerHTML;
    
    // Show loading state
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting...';
    confirmBtn.disabled = true;
    
    // Send delete request
    fetch(`/scripts/${scriptId}/delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            throw new Error('Delete failed');
        }
    })
    .catch(error => {
        confirmBtn.innerHTML = originalText;
        confirmBtn.disabled = false;
        showToast('Error', 'Failed to delete script', 'danger');
    });
}

// Python settings functionality
function initializePythonSettings() {
    // Only run on python settings page
    if (!document.getElementById('interpreterSelect')) return;
    
    window.selectInterpreter = function(select) {
        const selectedPath = select.value;
        if (selectedPath) {
            document.getElementById('pythonPath').value = selectedPath;
        }
    };
    
    window.testPythonInterpreter = function() {
        const pythonPath = document.getElementById('pythonPath').value;
        if (!pythonPath) {
            showToast('Error', 'Please enter a Python interpreter path', 'danger');
            return;
        }
        
        const testBtn = document.querySelector('button[onclick="testPythonInterpreter()"]');
        const originalText = testBtn.innerHTML;
        
        // Show loading state
        testBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Testing...';
        testBtn.disabled = true;
        
        // Send test request
        fetch('/settings/python/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ python_path: pythonPath })
        })
        .then(response => response.json())
        .then(data => {
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
            
            const resultDiv = document.getElementById('testResult');
            if (data.success) {
                resultDiv.className = 'test-result success';
                resultDiv.textContent = data.output;
            } else {
                resultDiv.className = 'test-result error';
                resultDiv.textContent = data.error;
            }
        })
        .catch(error => {
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
            showToast('Error', 'Failed to test interpreter', 'danger');
        });
    };
}

// Terminal functionality
function initializeTerminal() {
    // Only run on terminal page
    if (!document.getElementById('terminalContainer')) return;
    
    const terminalContainer = document.getElementById('terminalContainer');
    const commandInput = document.getElementById('commandInput');
    
    if (commandInput) {
        commandInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                executeCommand();
            }
        });
    }
    
    window.executeCommand = function() {
        const command = commandInput.value.trim();
        if (!command) return;
        
        // Add command to terminal display
        addToTerminal('$ ' + command, 'terminal-command');
        
        // Clear input
        commandInput.value = '';
        
        // Execute command
        fetch('/terminal/execute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command: command })
        })
        .then(response => response.json())
        .then(data => {
            if (data.output) {
                addToTerminal(data.output, data.success ? 'terminal-success' : 'terminal-error');
            }
        })
        .catch(error => {
            addToTerminal('Error executing command', 'terminal-error');
        });
    };
    
    function addToTerminal(text, className) {
        const line = document.createElement('div');
        line.className = className;
        line.textContent = text;
        terminalContainer.appendChild(line);
        
        // Scroll to bottom
        terminalContainer.scrollTop = terminalContainer.scrollHeight;
    }
}

// Execution detail functionality
function initializeExecutionDetail() {
    // Only run on execution detail page
    if (!document.getElementById('executionStatus')) return;
    
    const executionId = window.location.pathname.split('/').pop();
    let pollInterval = null;
    
    // Start polling for updates if execution is running
    const status = document.getElementById('executionStatus').textContent.toLowerCase();
    if (status.includes('running') || status.includes('pending')) {
        startPolling();
    }
    
    function startPolling() {
        pollInterval = setInterval(function() {
            fetch(`/execution/${executionId}/status`)
            .then(response => response.json())
            .then(data => {
                // Update status
                document.getElementById('executionStatus').innerHTML = data.status_display;
                
                // Update output if available
                if (data.output && document.getElementById('outputContainer')) {
                    document.getElementById('outputContainer').textContent = data.output;
                }
                
                // Stop polling if execution is complete
                if (!data.is_running) {
                    stopPolling();
                    
                    // Show stop button as disabled or hide it
                    const stopBtn = document.getElementById('stopExecutionBtn');
                    if (stopBtn) {
                        stopBtn.disabled = true;
                        stopBtn.innerHTML = '<i class="bi bi-check me-2"></i>Completed';
                    }
                }
            })
            .catch(error => {
                console.error('Error polling execution status:', error);
            });
        }, 2000); // Poll every 2 seconds
    }
    
    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }
    
    // Stop execution functionality
    window.stopExecution = function() {
        const stopBtn = document.getElementById('stopExecutionBtn');
        const originalText = stopBtn.innerHTML;
        
        // Show loading state
        stopBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Stopping...';
        stopBtn.disabled = true;
        
        fetch(`/execution/${executionId}/stop`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                stopBtn.innerHTML = '<i class="bi bi-stop me-2"></i>Stopped';
                showToast('Success', 'Execution stopped successfully', 'success');
                setTimeout(() => location.reload(), 1000);
            } else {
                stopBtn.innerHTML = originalText;
                stopBtn.disabled = false;
                showToast('Error', data.error || 'Failed to stop execution', 'danger');
            }
        })
        .catch(error => {
            stopBtn.innerHTML = originalText;
            stopBtn.disabled = false;
            showToast('Error', 'Failed to stop execution', 'danger');
        });
    };
    
    // Clean up polling when page is unloaded
    window.addEventListener('beforeunload', function() {
        stopPolling();
    });
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});