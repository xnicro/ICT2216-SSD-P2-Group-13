// Dummy data
// const data = Array.from({ length: 50 }, (_, i) => ({
//   id: i + 1,
//   name: `User ${i + 1}`,
//   email: `user${i + 1}@example.com`
// }));

const rowsPerPage = 5;
let currentPage = 1;

function renderTable(page) {
  const tableBody = document.querySelector("#dataTable tbody");
  tableBody.innerHTML = "";

  const start = (page - 1) * rowsPerPage;
  const end = start + rowsPerPage;
  const pageData = home_reports.slice(start, end);
  console.log(pageData);

  pageData.forEach(row => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.title}</td>
    <td>${row.created_at}</td>
    <td>${row.category_name}</td>
    <td>${row.status_name}</td>
    <td>${row.user_id}</td>`;
    tableBody.appendChild(tr);
  });

  renderPagination(pageData);
}

function renderPagination(pageData) {
  const pagination = document.getElementById("pagination");
  pagination.innerHTML = "";

  const pageCount = Math.ceil(pageData.length / rowsPerPage);

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
