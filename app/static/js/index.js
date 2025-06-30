// Mapping of category values to display labels
const CATEGORY_LABELS = {
  fires: 'Fires',
  faulty_facilities: 'Faulty Facilities/Equipment',
  vandalism: 'Vandalism',
  suspicious_activity: 'Suspicious Activity',
  other: 'Others'
};

const rowsPerPage = 5;
let currentPage = 1;

function renderTable(page) {
  const tableBody = document.querySelector("#dataTable tbody");
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

  const pageCount = Math.ceil(home_reports.length / rowsPerPage);

  for (let i = 1; i <= pageCount; i++) {
    const btn = document.createElement("button");
    btn.textContent = i;
    if (i === currentPage) btn.classList.add("active");

    btn.addEventListener("click", () => {
      currentPage = i;
      renderTable(currentPage);
    });

    pagination.appendChild(btn);
  }
}

// Initial render
renderTable(currentPage);
