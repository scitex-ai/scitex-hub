/**
 * Visitor Status Page - Live Countdown and Auto-refresh
 */

/**
 * Update countdown timers for allocated slots
 */
function updateCountdowns(): void {
    document.querySelectorAll('.slot-time-remaining span').forEach(function(element) {
        const htmlElement = element as HTMLElement;
        const text = htmlElement.textContent?.trim() || '';
        const match = text.match(/Expires in (\d+) min/);

        if (match) {
            let minutes = parseInt(match[1]);
            let totalSeconds = minutes * 60;

            // Store initial time if not already stored
            if (!htmlElement.dataset.initialSeconds) {
                htmlElement.dataset.initialSeconds = totalSeconds.toString();
                htmlElement.dataset.startTime = Date.now().toString();
            }

            // Calculate elapsed seconds since page load
            const elapsedSeconds = Math.floor((Date.now() - parseInt(htmlElement.dataset.startTime || '0')) / 1000);
            const remainingSeconds = Math.max(0, parseInt(htmlElement.dataset.initialSeconds || '0') - elapsedSeconds);

            // Convert to minutes
            const remainingMinutes = Math.floor(remainingSeconds / 60);

            // Update display
            htmlElement.textContent = `Expires in ${remainingMinutes} min`;

            // Reload page if expired
            if (remainingSeconds <= 0) {
                location.reload();
            }
        }
    });
}

// Update countdowns every second
setInterval(updateCountdowns, 1000);
updateCountdowns(); // Initial call

// Refresh page every 60 seconds to get server updates
setTimeout(function() {
    location.reload();
}, 60000);
