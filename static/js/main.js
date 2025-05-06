// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-hide flash messages after 5 seconds
    var flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            var alert = new bootstrap.Alert(message);
            alert.close();
        }, 5000);
    });

    // Handle form submissions
    var forms = document.querySelectorAll('form[data-ajax="true"]');
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            var formData = new FormData(form);
            
            fetch(form.action, {
                method: form.method,
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    showAlert('success', data.message);
                    // Reload page or update content
                    if (data.redirect) {
                        window.location.href = data.redirect;
                    }
                } else {
                    // Show error message
                    showAlert('danger', data.message);
                }
            })
            .catch(error => {
                showAlert('danger', 'An error occurred. Please try again.');
            });
        });
    });

    // File input preview
    const fileInputs = document.querySelectorAll('.custom-file-input');
    fileInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const fileName = e.target.files[0]?.name || 'Choose file';
            const label = this.nextElementSibling;
            label.textContent = fileName;
        });
    });

    // Delete confirmation
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const form = this.closest('form');
            
            if (confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                form.submit();
            }
        });
    });

    // Media library
    const mediaGrid = document.querySelector('.media-grid');
    if (mediaGrid) {
        // Image preview
        const mediaItems = mediaGrid.querySelectorAll('.media-item img');
        mediaItems.forEach(img => {
            img.addEventListener('click', function() {
                const src = this.src;
                const alt = this.alt;
                
                const modal = new bootstrap.Modal(document.getElementById('imagePreviewModal'));
                const modalImg = document.querySelector('#imagePreviewModal img');
                modalImg.src = src;
                modalImg.alt = alt;
                modal.show();
            });
        });

        // Delete media
        const deleteMediaButtons = mediaGrid.querySelectorAll('.delete-media');
        deleteMediaButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                if (confirm('Are you sure you want to delete this media? This action cannot be undone.')) {
                    const form = this.closest('form');
                    form.submit();
                }
            });
        });
    }

    // Form validation
    const formsValidation = document.querySelectorAll('.needs-validation');
    formsValidation.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
});

// Function to show alert messages
function showAlert(type, message) {
    var alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    var container = document.querySelector('main');
    container.insertBefore(alertDiv, container.firstChild);
    
    // Auto-hide after 5 seconds
    setTimeout(function() {
        var alert = new bootstrap.Alert(alertDiv);
        alert.close();
    }, 5000);
}

// Function to confirm delete actions
function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

// Function to handle file input changes
function handleFileInput(input) {
    var fileName = input.files[0]?.name;
    if (fileName) {
        var label = input.nextElementSibling;
        label.textContent = fileName;
    }
} 