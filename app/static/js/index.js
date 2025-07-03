// Mapping of category values to display labels
// const CATEGORY_LABELS = {
//   fires: 'Fires',
//   faulty_facilities: 'Faulty Facilities/Equipment',
//   vandalism: 'Vandalism',
//   suspicious_activity: 'Suspicious Activity',
//   other: 'Others'
// };

const rowsPerPage = 7;
let currentPage = 1;
let currentCategory = "";
let currentDateSort = "";
let currentStatus = "";

function renderTable(page) {
  const tableBody = document.querySelector("#reportTable tbody");
  tableBody.innerHTML = "";

  // Filter by category
  let filteredData = home_reports.filter(row => {
    const categoryMatch = !currentCategory || row.category_name === currentCategory;
    const statusMatch = !currentStatus || row.status_name.toLowerCase() === currentStatus.toLowerCase();
    return categoryMatch && statusMatch;
  });

  // Sort by date
  filteredData.sort((a, b) => {
    if (currentDateSort === "oldest") {
      return new Date(a.created_at) - new Date(b.created_at);
    } else {
      return new Date(b.created_at) - new Date(a.created_at); // newest first
    }
  });

  // Paginate
  const totalPages = Math.ceil(filteredData.length / rowsPerPage);
  page = Math.min(Math.max(page, 1), totalPages);
  const start = (page - 1) * rowsPerPage;
  const end = start + rowsPerPage;
  const pageData = filteredData.slice(start, end);

  pageData.forEach(row => {
    const tr = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.textContent = row.title;

    const rawDate = new Date(row.created_at);

    // Format date: "July 1, 2025"
    const dateOptions = { year: "numeric", month: "long", day: "numeric" };
    const formattedDate = rawDate.toLocaleDateString("en-US", dateOptions);

    // Format time: "12.10pm"
    let hours = rawDate.getHours();
    const minutes = rawDate.getMinutes().toString().padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    const formattedTime = `${hours}:${minutes} ${ampm}`;

    // Create date <td>
    const dateCell = document.createElement("td");
    dateCell.textContent = formattedDate;

    // Create time <td>
    const timeCell = document.createElement("td");
    timeCell.textContent = formattedTime;

    const categoryCell = document.createElement("td");
    categoryCell.textContent = row.category_name;

    const statusCell = document.createElement("td");
    const statusSpan = document.createElement("span");
    statusSpan.textContent = row.status_name;
    const statusClass = `status-${row.status_name.toLowerCase().replace(/\s+/g, '-')}`;
    statusSpan.classList.add("status-badge", statusClass);
    statusCell.appendChild(statusSpan);

    const ownerCell = document.createElement("td");
    ownerCell.textContent = row.user_id;
    console.log(row);

    // Append cells to the row
    tr.appendChild(titleCell);
    tr.appendChild(dateCell);
    tr.appendChild(timeCell);
    tr.appendChild(categoryCell);
    tr.appendChild(statusCell);
    tr.appendChild(ownerCell);

    tableBody.appendChild(tr);
  });

  renderPagination(filteredData.length);
}

function renderPagination(dataLength) {
  const pagination = document.getElementById("pagination");
  pagination.innerHTML = "";

  const totalPages = Math.ceil(dataLength / rowsPerPage);
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
  let endPage = startPage + maxVisible - 1;

  if (endPage > totalPages) {
    endPage = totalPages;
    startPage = Math.max(1, endPage - maxVisible + 1);
  }

  for (let i = startPage; i <= endPage; i++) {
    pagination.appendChild(createButton(i, i, false, i === currentPage));
  }

  // Next button
  pagination.appendChild(createButton('<i class="fa-solid fa-chevron-right"></i>', currentPage + 1, currentPage === totalPages));
}

// Initial render
renderTable(currentPage);

document.getElementById("categoryFilter").addEventListener("change", (e) => {
  currentCategory = e.target.value;
  currentPage = 1;
  renderTable(currentPage);
});

document.getElementById("statusFilter").addEventListener("change", (e) => {
  currentStatus = e.target.value;
  currentPage = 1;
  renderTable(currentPage);
});

document.getElementById("dateFilter").addEventListener("change", (e) => {
  currentDateSort = e.target.value;
  currentPage = 1;
  renderTable(currentPage);
});
