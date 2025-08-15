// ScriptFlow JavaScript Functions

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Confirm delete actions
    var deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            var message = this.getAttribute('data-confirm-delete') || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // File upload preview
    var fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            var file = e.target.files[0];
            var previewElement = document.getElementById(this.id + '_preview');
            
            if (file && previewElement) {
                var fileName = file.name;
                var fileSize = (file.size / 1024 / 1024).toFixed(2) + ' MB';
                
                previewElement.innerHTML = 
                    '<div class="alert alert-info mt-2">' +
                    '<i class="bi bi-file-earmark-code me-2"></i>' +
                    '<strong>' + fileName + '</strong> (' + fileSize + ')' +
                    '</div>';
            }
        });
    });
    
    // Real-time log updates
    if (window.location.pathname.includes('/logs/execution/')) {
        var executionId = window.location.pathname.split('/').pop();
        if (executionId && !isNaN(executionId)) {
            startLogPolling(executionId);
        }
    }
    
    // Form validation
    var forms = document.querySelectorAll('.needs-validation');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
});

// Real-time log polling for execution details
function startLogPolling(executionId) {
    var pollInterval = 2000; // 2 seconds
    var maxPolls = 300; // 10 minutes max
    var pollCount = 0;
    
    function pollLogs() {
        if (pollCount >= maxPolls) {
            console.log('Log polling stopped: max polls reached');
            return;
        }
        
        fetch('/logs/execution/' + executionId + '/output')
            .then(response => response.json())
            .then(data => {
                pollCount++;
                
                // Update status
                var statusElement = document.getElementById('execution-status');
                if (statusElement) {
                    statusElement.innerHTML = 
                        '<span class="status-indicator status-' + getStatusColor(data.status) + '">' +
                        getStatusIcon(data.status) + ' ' + 
                        data.status.charAt(0).toUpperCase() + data.status.slice(1) +
                        '</span>';
                }
                
                // Update duration
                var durationElement = document.getElementById('execution-duration');
                if (durationElement && data.duration) {
                    durationElement.textContent = data.duration;
                }
                
                // Update output
                var stdoutElement = document.getElementById('execution-stdout');
                if (stdoutElement && data.stdout) {
                    stdoutElement.textContent = data.stdout;
                }
                
                var stderrElement = document.getElementById('execution-stderr');
                if (stderrElement && data.stderr) {
                    stderrElement.textContent = data.stderr;
                    stderrElement.parentElement.style.display = data.stderr ? 'block' : 'none';
                }
                
                // Update cancel button
                var cancelButton = document.getElementById('cancel-execution-btn');
                if (cancelButton) {
                    if (data.is_running) {
                        cancelButton.style.display = 'inline-block';
                    } else {
                        cancelButton.style.display = 'none';
                    }
                }
                
                // Continue polling if still running
                if (data.is_running) {
                    setTimeout(pollLogs, pollInterval);
                } else {
                    console.log('Log polling stopped: execution finished');
                    // Reload page after a short delay to show final state
                    setTimeout(function() {
                        location.reload();
                    }, 2000);
                }
            })
            .catch(error => {
                console.error('Error polling logs:', error);
                pollCount++;
                if (pollCount < maxPolls) {
                    setTimeout(pollLogs, pollInterval * 2); // Retry with longer interval
                }
            });
    }
    
    // Start polling
    pollLogs();
}

// Helper functions for status display
function getStatusColor(status) {
    switch(status) {
        case 'completed': return 'success';
        case 'failed': return 'danger';
        case 'timeout': return 'warning';
        case 'running': return 'warning';
        case 'cancelled': return 'secondary';
        default: return 'secondary';
    }
}

function getStatusIcon(status) {
    switch(status) {
        case 'completed': return '✅';
        case 'failed': return '❌';
        case 'timeout': return '⏰';
        case 'running': return '🔄';
        case 'cancelled': return '🛑';
        case 'pending': return '⏳';
        default: return '❓';
    }
}

// Cancel execution
function cancelExecution(executionId) {
    if (!confirm('Are you sure you want to cancel this execution?')) {
        return;
    }
    
    var button = document.getElementById('cancel-execution-btn');
    var originalText = button.innerHTML;
    
    // Show loading state
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Cancelling...';
    button.disabled = true;
    
    fetch('/logs/execution/' + executionId + '/cancel', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showAlert('Execution cancelled successfully', 'success');
            // Hide cancel button
            button.style.display = 'none';
        } else {
            // Show error message
            showAlert(data.message || 'Failed to cancel execution', 'danger');
            // Restore button
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error cancelling execution:', error);
        showAlert('Error cancelling execution', 'danger');
        // Restore button
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Show alert message
function showAlert(message, type) {
    var alertsContainer = document.querySelector('.container .alert');
    if (!alertsContainer) {
        alertsContainer = document.querySelector('.container');
    }
    
    var alert = document.createElement('div');
    alert.className = 'alert alert-' + type + ' alert-dismissible fade show';
    alert.innerHTML = 
        '<i class="bi bi-' + getAlertIcon(type) + ' me-2"></i>' +
        message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
    
    alertsContainer.insertBefore(alert, alertsContainer.firstChild);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        var bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

function getAlertIcon(type) {
    switch(type) {
        case 'success': return 'check-circle';
        case 'danger': return 'exclamation-triangle';
        case 'warning': return 'exclamation-triangle';
        case 'info': return 'info-circle';
        default: return 'info-circle';
    }
}

// Schedule form helpers
function updateScheduleFields() {
    var frequency = document.getElementById('frequency');
    if (!frequency) return;
    
    var dailyFields = document.getElementById('daily-fields');
    var weeklyFields = document.getElementById('weekly-fields');
    var monthlyFields = document.getElementById('monthly-fields');
    
    // Hide all fields first
    if (dailyFields) dailyFields.style.display = 'none';
    if (weeklyFields) weeklyFields.style.display = 'none';
    if (monthlyFields) monthlyFields.style.display = 'none';
    
    // Show relevant fields
    switch(frequency.value) {
        case 'daily':
            if (dailyFields) dailyFields.style.display = 'block';
            break;
        case 'weekly':
            if (weeklyFields) weeklyFields.style.display = 'block';
            break;
        case 'monthly':
            if (monthlyFields) monthlyFields.style.display = 'block';
            break;
    }
    
    updateSchedulePreview();
}

function updateSchedulePreview() {
    var previewElement = document.getElementById('schedule-preview');
    if (!previewElement) return;
    
    var frequency = document.getElementById('frequency');
    if (!frequency) return;
    
    var preview = 'Schedule preview will appear here';
    
    switch(frequency.value) {
        case 'hourly':
            preview = 'Runs every hour on the hour';
            break;
        case 'daily':
            var time = document.getElementById('daily_time');
            if (time && time.value) {
                preview = 'Runs daily at ' + time.value;
            }
            break;
        case 'weekly':
            var time = document.getElementById('weekly_time');
            var days = document.querySelectorAll('input[name="weekly_days"]:checked');
            if (time && time.value && days.length > 0) {
                var dayNames = Array.from(days).map(d => d.value).join(', ');
                preview = 'Runs weekly on ' + dayNames + ' at ' + time.value;
            }
            break;
        case 'monthly':
            var time = document.getElementById('monthly_time');
            var day = document.getElementById('monthly_day');
            if (time && time.value && day && day.value) {
                preview = 'Runs monthly on day ' + day.value + ' at ' + time.value;
            }
            break;
    }
    
    previewElement.textContent = preview;
}