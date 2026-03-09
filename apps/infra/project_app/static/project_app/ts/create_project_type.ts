/**
 * Project Type Toggle - Handles switching between local and remote project types
 */

function toggleProjectType(): void {
    const projectTypeInput = document.querySelector('input[name="project_type"]:checked') as HTMLInputElement;
    if (!projectTypeInput) {
        console.error('[CreateProjectType] No project type radio button checked');
        return;
    }

    const projectType = projectTypeInput.value;
    const localOptions = document.getElementById('local-init-options');
    const remoteFields = document.getElementById('remote-project-fields');

    if (!localOptions || !remoteFields) {
        console.error('[CreateProjectType] Required elements not found');
        return;
    }

    if (projectType === 'local') {
        localOptions.style.display = 'block';
        remoteFields.style.display = 'none';
    } else if (projectType === 'remote') {
        localOptions.style.display = 'none';
        remoteFields.style.display = 'block';
    }

    console.log('[CreateProjectType] Toggled to:', projectType);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('[CreateProjectType] Initializing project type toggle');
    toggleProjectType();

    // Add change listeners to radio buttons
    const radioButtons = document.querySelectorAll('input[name="project_type"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', toggleProjectType);
    });
});

// Export for potential external use
if (typeof window !== 'undefined') {
    (window as any).toggleProjectType = toggleProjectType;
}
