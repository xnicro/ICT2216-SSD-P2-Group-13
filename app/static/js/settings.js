// Function to toggle section visibility with animation
function toggleSection(sectionId) {
  const section = document.getElementById(sectionId).parentElement;
  section.classList.toggle('active');
}

// Initialize all sections as collapsed
document.addEventListener("DOMContentLoaded", () => {
  const sections = document.querySelectorAll('.section');
  sections.forEach(section => {
    section.classList.remove('active');
  });
});