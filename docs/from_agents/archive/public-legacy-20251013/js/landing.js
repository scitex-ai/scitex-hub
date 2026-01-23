/**
 * SciTeX Web - Landing Page JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize the landing page
  initLandingPage();
});

function initLandingPage() {
  // Toggle mobile menu
  const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
  const siteNavigation = document.querySelector('.site-navigation');
  
  if (mobileMenuToggle && siteNavigation) {
    mobileMenuToggle.addEventListener('click', () => {
      siteNavigation.classList.toggle('open');
    });
  }
  
  // Smooth scroll for navigation links
  const navLinks = document.querySelectorAll('.nav-link');
  
  navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const targetId = link.getAttribute('href');
      const targetElement = document.querySelector(targetId);
      
      if (targetElement) {
        // Remove active class from all links
        navLinks.forEach(navLink => {
          navLink.classList.remove('active');
        });
        
        // Add active class to clicked link
        link.classList.add('active');
        
        // Scroll to target element
        window.scrollTo({
          top: targetElement.offsetTop - 80, // Account for header height
          behavior: 'smooth'
        });
        
        // Close mobile menu if open
        if (siteNavigation.classList.contains('open')) {
          siteNavigation.classList.remove('open');
        }
      }
    });
  });
  
  // Pricing toggle functionality
  const pricingToggle = document.getElementById('pricing-toggle');
  const pricePeriods = document.querySelectorAll('.period');
  const prices = document.querySelectorAll('.price');
  
  // Store original monthly prices
  const monthlyPrices = Array.from(prices).map(price => price.textContent);
  
  if (pricingToggle) {
    pricingToggle.addEventListener('change', () => {
      const isAnnual = pricingToggle.checked;
      
      // Update period text
      pricePeriods.forEach(period => {
        period.textContent = isAnnual ? '/year' : '/month';
      });
      
      // Update prices (applying 20% discount for annual)
      prices.forEach((price, index) => {
        if (price.textContent !== 'Custom') {
          const monthlyPrice = parseFloat(monthlyPrices[index].replace('$', ''));
          if (!isNaN(monthlyPrice)) {
            if (isAnnual) {
              // Calculate annual price with 20% discount
              const annualPrice = monthlyPrice * 12 * 0.8;
              price.textContent = '$' + annualPrice.toFixed(0);
            } else {
              // Restore monthly price
              price.textContent = monthlyPrices[index];
            }
          }
        }
      });
    });
  }
  
  // FAQ accordion functionality
  const faqQuestions = document.querySelectorAll('.faq-question');
  
  faqQuestions.forEach(question => {
    question.addEventListener('click', () => {
      const answer = question.nextElementSibling;
      const isOpen = answer.style.maxHeight;
      
      // Close all other answers
      document.querySelectorAll('.faq-answer').forEach(item => {
        item.style.maxHeight = null;
      });
      
      // Toggle current answer
      if (!isOpen) {
        answer.style.maxHeight = answer.scrollHeight + 'px';
        question.classList.add('active');
      } else {
        question.classList.remove('active');
      }
    });
  });
  
  // Set up intersection observer for animations
  const animatedElements = document.querySelectorAll('.feature-alternating-item, .product-card, .benefit-item, .testimonial-card');
  
  if ('IntersectionObserver' in window) {
    const appearOptions = {
      threshold: 0.15,
      rootMargin: '0px 0px -100px 0px'
    };
    
    const appearOnScroll = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        
        entry.target.classList.add('appear');
        observer.unobserve(entry.target);
      });
    }, appearOptions);
    
    animatedElements.forEach(element => {
      element.classList.add('fade-in');
      appearOnScroll.observe(element);
    });
  }
}