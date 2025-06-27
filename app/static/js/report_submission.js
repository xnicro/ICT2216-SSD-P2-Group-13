// static/js/report.js

document.addEventListener('DOMContentLoaded', function() {
  const categorySelect = document.getElementById('category');
  const otherContainer = document.getElementById('other-desc-container');
  const otherInput = document.getElementById('category_description');

  if (!categorySelect) return; // safety

  categorySelect.addEventListener('change', () => {
    if (categorySelect.value === 'other') {
      otherContainer.style.display = 'block';
      otherInput.setAttribute('required', 'required');
    } else {
      otherContainer.style.display = 'none';
      otherInput.removeAttribute('required');
      otherInput.value = '';
    }
  });
});
