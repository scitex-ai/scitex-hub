/**
 * SciTeX Web - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize the application
  initApp();
});

function initApp() {
  console.log('SciTeX Web application initialized');
  
  // Add event listeners
  const getStartedBtn = document.querySelector('.btn-primary');
  if (getStartedBtn) {
    getStartedBtn.addEventListener('click', () => {
      console.log('Get Started clicked');
      // Add navigation or modal display logic here
    });
  }
}
