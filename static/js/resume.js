document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('resumeUploadForm');
    const fileInput = document.getElementById('resume');
    const fileInfo = document.getElementById('file-info');
    const submitBtn = document.getElementById('submitBtn');
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('results-section');
    const progressFill = document.getElementById('progress-fill');
    const progressMessage = document.getElementById('progress-message');
    
    let applicationId = null;
    let statusInterval = null;
    
    // File input handling
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            fileInfo.innerHTML = `
                <div class="file-info-details">
                    <span>📄 ${file.name}</span>
                    <span>${(file.size / 1024).toFixed(2)} KB</span>
                </div>
            `;
        } else {
            fileInfo.innerHTML = '';
        }
    });
    
    // Drag and drop handling
    // const dropArea = document.querySelector('.file-drop-area');
    // File input click trigger
const dropArea = document.querySelector('.file-drop-area');
const browseText = document.querySelector('.file-drop-area span'); // The "click to browse" text

// Make the entire drop area clickable
if (dropArea) {
    dropArea.addEventListener('click', function(e) {
        // Don't trigger if clicking on file info or other elements
        if (!e.target.closest('.file-info')) {
            fileInput.click();
        }
    });
}

// Also make the "click to browse" text explicitly clickable
if (browseText) {
    browseText.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        fileInput.click();
    });
}
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropArea.classList.add('highlight');
    }
    
    function unhighlight() {
        dropArea.classList.remove('highlight');
    }
    
    dropArea.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        fileInput.files = files;
        
        if (files.length > 0) {
            const file = files[0];
            fileInfo.innerHTML = `
                <div class="file-info-details">
                    <span>📄 ${file.name}</span>
                    <span>${(file.size / 1024).toFixed(2)} KB</span>
                </div>
            `;
        }
    }
    
    // Form submission
    uploadForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Validate form
        if (!validateForm()) {
            return;
        }
        
        // Show progress section
        uploadForm.style.display = 'none';
        progressSection.style.display = 'block';
        
        // Update steps
        updateStep('step-upload', 'completed');
        
        // Prepare form data
        const formData = new FormData(uploadForm);
        
        try {
            // Upload resume
            const response = await fetch('/upload-resume', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                applicationId = data.application_id;
                progressMessage.textContent = 'Upload successful. Starting analysis...';
                updateStep('step-upload', 'completed');
                updateStep('step-parse', 'active');
                
                // Start polling for status
                startStatusPolling(applicationId);
            } else {
                showError(data.error || 'Upload failed');
            }
        } catch (error) {
            showError('Network error. Please try again.');
            console.error('Upload error:', error);
        }
    });
    
    function validateForm() {
        const jobId = document.getElementById('job_id').value;
        const name = document.getElementById('candidate_name').value;
        const email = document.getElementById('candidate_email').value;
        const file = fileInput.files[0];
        
        if (!jobId) {
            alert('Please select a job position');
            return false;
        }
        
        if (!name.trim()) {
            alert('Please enter your name');
            return false;
        }
        
        if (!email.trim() || !isValidEmail(email)) {
            alert('Please enter a valid email');
            return false;
        }
        
        if (!file) {
            alert('Please select a resume file');
            return false;
        }
        
        // Check file size (5MB)
        if (file.size > 5 * 1024 * 1024) {
            alert('File size must be less than 5MB');
            return false;
        }
        
        // Check file type
        const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain'];
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|docx|txt)$/i)) {
            alert('Please upload PDF, DOCX, or TXT files only');
            return false;
        }
        
        return true;
    }
    
    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }
    
    function startStatusPolling(appId) {
        statusInterval = setInterval(async () => {
            try {
                const response = await fetch(`/resume-status/${appId}`);
                const status = await response.json();
                
                updateProgress(status);
                
                if (status.status === 'completed') {
                    clearInterval(statusInterval);
                    setTimeout(() => {
                        window.location.href = `/resume-results/${appId}`;
                    }, 1000);
                } else if (status.status === 'failed') {
                    clearInterval(statusInterval);
                    showError(status.message || 'Processing failed');
                }
            } catch (error) {
                console.error('Status polling error:', error);
            }
        }, 2000);
    }
    
    function updateProgress(status) {
        // Update progress bar
        progressFill.style.width = `${status.progress}%`;
        progressMessage.textContent = status.message;
        
        // Update steps based on progress
        if (status.progress >= 20) {
            updateStep('step-parse', 'completed');
            updateStep('step-semantic', 'active');
        }
        if (status.progress >= 40) {
            updateStep('step-semantic', 'completed');
            updateStep('step-bert', 'active');
        }
        if (status.progress >= 60) {
            updateStep('step-bert', 'completed');
            updateStep('step-scoring', 'active');
        }
        if (status.progress >= 80) {
            updateStep('step-scoring', 'completed');
            updateStep('step-complete', 'active');
        }
        if (status.progress >= 100) {
            updateStep('step-complete', 'completed');
        }
    }
    
    function updateStep(stepId, state) {
        const step = document.getElementById(stepId);
        if (!step) return;
        
        // Remove existing states
        step.classList.remove('active', 'completed');
        
        // Add new state
        step.classList.add(state);
        
        // Update icon based on state
        if (state === 'completed') {
            step.innerHTML = step.innerHTML.replace('⏳', '✅').replace('⚙️', '✅').replace('🔄', '✅');
        } else if (state === 'active') {
            if (stepId === 'step-parse') step.innerHTML = '⚙️ Parsing';
            else if (stepId === 'step-semantic') step.innerHTML = '🔄 Semantic Analysis';
            else if (stepId === 'step-bert') step.innerHTML = '🤖 BERT Matching';
            else if (stepId === 'step-scoring') step.innerHTML = '📊 Scoring';
            else if (stepId === 'step-complete') step.innerHTML = '⏳ Complete';
        }
    }
    
    function showError(message) {
        progressSection.style.display = 'none';
        uploadForm.style.display = 'block';
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `
            <span>❌</span>
            <p>${message}</p>
        `;
        
        uploadForm.insertBefore(errorDiv, uploadForm.firstChild);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
});