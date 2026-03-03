/**
 * Search Stepper Control
 *
 * Controls the horizontal progress stepper: Ready -> Searching -> Done
 */
let searchStartTime = 0;
let timerInterval = null;
/**
 * Set stepper to searching state and start timer
 */
export function showToolbarStatus(message = "Searching...") {
    const step1 = document.getElementById("step1");
    const step2 = document.getElementById("step2");
    const step3 = document.getElementById("step3");
    const line1 = document.getElementById("line1");
    // Ready = complete, Searching = active/searching
    step1?.classList.remove("active");
    step1?.classList.add("complete");
    step2?.classList.add("active", "searching");
    step3?.classList.remove("active", "complete", "done");
    line1?.classList.add("active");
    // Start timer
    searchStartTime = Date.now();
    startTimer();
}
function startTimer() {
    if (timerInterval)
        clearInterval(timerInterval);
    const timerEl = document.getElementById("searchTimer");
    timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - searchStartTime) / 1000);
        if (timerEl)
            timerEl.textContent = `${elapsed}s`;
    }, 100);
}
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    return Math.floor((Date.now() - searchStartTime) / 1000);
}
/**
 * Update progress during search
 */
export function updateProgressStep(completed, total) {
    const stepText2 = document.getElementById("stepText2");
    if (stepText2)
        stepText2.textContent = `Searching ${completed}/${total}`;
}
/**
 * Reset stepper to ready state
 */
export function resetToolbarStatus() {
    stopTimer();
    const step1 = document.getElementById("step1");
    const step2 = document.getElementById("step2");
    const step3 = document.getElementById("step3");
    const line1 = document.getElementById("line1");
    const line2 = document.getElementById("line2");
    const stepText2 = document.getElementById("stepText2");
    const stepText3 = document.getElementById("stepText3");
    // Reset all classes
    step1?.classList.remove("complete", "searching", "done");
    step1?.classList.add("active");
    step2?.classList.remove("active", "complete", "searching", "done");
    step3?.classList.remove("active", "complete", "searching", "done");
    line1?.classList.remove("active");
    line2?.classList.remove("active");
    // Reset labels
    if (stepText2)
        stepText2.textContent = "Searching";
    if (stepText3)
        stepText3.textContent = "Done";
}
/**
 * Hide toolbar (alias for reset)
 */
export function hideToolbarStatus() {
    resetToolbarStatus();
}
/**
 * Set stepper to complete state
 */
export function updateToolbarStatus(message, isComplete = false) {
    if (isComplete) {
        const elapsed = stopTimer();
        const step1 = document.getElementById("step1");
        const step2 = document.getElementById("step2");
        const step3 = document.getElementById("step3");
        const line1 = document.getElementById("line1");
        const line2 = document.getElementById("line2");
        const stepText3 = document.getElementById("stepText3");
        // All steps complete, Done is active with blue color
        step1?.classList.remove("active", "searching");
        step1?.classList.add("complete");
        step2?.classList.remove("active", "searching");
        step2?.classList.add("complete");
        step3?.classList.remove("active", "searching");
        step3?.classList.add("done");
        line1?.classList.add("active");
        line2?.classList.add("active");
        // Update done label with count and time
        if (stepText3)
            stepText3.textContent = `${message} (${elapsed}s)`;
        setTimeout(() => resetToolbarStatus(), 4000);
    }
}
//# sourceMappingURL=toolbar-status.ts.map
