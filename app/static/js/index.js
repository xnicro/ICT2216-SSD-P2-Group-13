// Mapping of category values to display labels
const CATEGORY_LABELS = {
  fires: 'Fires',
  faulty_facilities: 'Faulty Facilities/Equipment',
  vandalism: 'Vandalism',
  suspicious_activity: 'Suspicious Activity',
  other: 'Others'
};

const rowsPerPage = 7;
let currentPage = 1;

function renderTable(page) {
  const tableBody = document.querySelector("#reportTable tbody");
  tableBody.innerHTML = "";

  const start = (page - 1) * rowsPerPage;
  const end = start + rowsPerPage;
  const pageData = home_reports.slice(start, end);

  pageData.forEach(row => {
    const displayCategory = CATEGORY_LABELS[row.category_name] || row.category_name;
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.title}</td>
      <td>${row.created_at}</td>
      <td>${displayCategory}</td>
      <td>${row.status_name}</td>
      <td>${row.user_id}</td>
    `;
    tableBody.appendChild(tr);
  });

  renderPagination();
}

function renderPagination() {
  const pagination = document.getElementById("pagination");
  pagination.innerHTML = "";

  const totalPages = Math.ceil(home_reports.length / rowsPerPage);
  const maxVisible = 5;

  const createButton = (text, page = null, disabled = false, active = false) => {
    const btn = document.createElement("button");
    btn.innerHTML = text;
    btn.disabled = disabled;
    if (active) btn.classList.add("active");
    if (page !== null) {
      btn.addEventListener("click", () => {
        currentPage = page;
        renderTable(currentPage);
      });
    }
    return btn;
  };

  // Prev button
  pagination.appendChild(createButton('<i class="fa-solid fa-chevron-left"></i>', currentPage - 1, currentPage === 1));

  let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  console.log(startPage);
  let endPage = startPage + maxVisible - 1;
  console.log(endPage);

  if (endPage > totalPages) {
    endPage = totalPages;
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  // Leading ellipsis
  if (startPage > 1) {
    pagination.appendChild(createButton("1", 1));
    if (startPage > 2) {
      pagination.appendChild(createButton("...", null, true));
    }
  }

  for (let i = startPage; i <= endPage; i++) {
    pagination.appendChild(createButton(i, i, false, i === currentPage));
  }

  // Trailing ellipsis
  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      pagination.appendChild(createButton("...", null, true));
    }
    pagination.appendChild(createButton(totalPages, totalPages));
  }

  // Next button
  pagination.appendChild(createButton('<i class="fa-solid fa-chevron-right"></i>', currentPage + 1, currentPage === totalPages));
}

// Initial render
renderTable(currentPage);
