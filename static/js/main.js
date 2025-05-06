// Initialize tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
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
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // AJAX form submission
    const ajaxForms = document.querySelectorAll('.ajax-form');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: this.method,
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show success message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-success alert-dismissible fade show';
                    alert.innerHTML = `
                        ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    form.insertAdjacentElement('beforebegin', alert);

                    // Redirect if specified
                    if (data.redirect) {
                        setTimeout(() => {
                            window.location.href = data.redirect;
                        }, 1500);
                    }
                } else {
                    // Show error message
                    const alert = document.createElement('div');
                    alert.className = 'alert alert-danger alert-dismissible fade show';
                    alert.innerHTML = `
                        ${data.message}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    `;
                    form.insertAdjacentElement('beforebegin', alert);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const alert = document.createElement('div');
                alert.className = 'alert alert-danger alert-dismissible fade show';
                alert.innerHTML = `
                    An error occurred. Please try again.
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                form.insertAdjacentElement('beforebegin', alert);
            });
        });
    });
}); 