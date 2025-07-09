function showFlashMessage(message, type = "success") {
  const container = document.getElementById("flashMessageContainer");
  if (!container) return;

  const div = document.createElement("div");
  div.className = `flash-message flash-${type}`;
  div.textContent = message;

  container.appendChild(div);

  setTimeout(() => {
    div.remove();
  }, 4000); 
}

document.addEventListener("DOMContentLoaded", function () {
  // === State & References ===
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const tableBody = document.getElementById("reportsTableBody");
  const originalRows = Array.from(tableBody.querySelectorAll("tr"));
  const rowsPerPage = 7;
  const CATEGORY_MAPPING = {
    'all': 'All',
    'fires': 'Fires',
    'faulty_facilities': 'Faulty Facilities/Equipment',
    'vandalism': 'Vandalism',
    'suspicious_activity': 'Suspicious Activity',
    'other': 'Others'
  };
  const VALID_CATEGORY_OPTIONS = Object.keys(CATEGORY_MAPPING).concat("all");
  const VALID_SORT_OPTIONS = [
    "id-asc",
    "id-desc",
    "desc-asc",
    "desc-desc"
  ];
  const allRows = [...originalRows];
  let currentStatusFilter = "all";
  let selectedReportId = null;
  let selectedRow = null;

  const searchInput = document.getElementById("searchInput");
  const sortSelect = document.getElementById("sortSelect");
  const filterCategory = document.getElementById("filterCategory");
  const paginationContainer = document.getElementById("paginationContainer");

  // === Status Update ===
  document.querySelectorAll(".options input[type='radio']").forEach(radio => {
    radio.addEventListener("change", handleStatusChange);
  });

  function handleStatusChange(event) {
    const radio = event.target;
    const reportId = radio.name.split('-')[1];
    const selectedLabel = document.querySelector(`label[for='${radio.id}']`);
    const statusText = selectedLabel?.dataset.txt;
    const statusId = parseInt(radio.id.split('-')[1]);

    if (!/^\d+$/.test(reportId) || isNaN(statusId)) return;

    const selectedDiv = radio.closest(".select")?.querySelector(".selected");
    if (!selectedDiv || !statusText) return;

    const arrowSvg = selectedDiv.querySelector("svg");
    selectedDiv.textContent = "";
    selectedDiv.append(document.createTextNode(statusText));
    if (arrowSvg) selectedDiv.appendChild(arrowSvg);
    selectedDiv.dataset.default = statusText;

    fetch("/update_status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify({ report_id: reportId, status_id: statusId })
    })
      .then(res => res.ok ? res.json() : Promise.reject(res))
      .then(data => {
        if (!data.success) {
          showFlashMessage("Failed to update status.", "error");
          return;
        }

        const row = selectedDiv.closest("tr");
        const badge = row.querySelector(".status-badge");
        badge.textContent = statusText;
        badge.className = `status-badge status-${statusText.toLowerCase()}`;

        const optionsDiv = row.querySelector(".options");
        optionsDiv.textContent = "";

        ALL_STATUSES.forEach(status => {
          if (status.name.toLowerCase() !== statusText.toLowerCase()) {
            const div = document.createElement("div");
            div.title = `option-${status.status_id}`;

            const input = document.createElement("input");
            input.type = "radio";
            input.name = `option-${reportId}`;
            input.id = `option-${status.status_id}-${reportId}`;

            const label = document.createElement("label");
            label.className = "option";
            label.htmlFor = input.id;
            label.dataset.txt = status.name.charAt(0).toUpperCase() + status.name.slice(1);

            div.appendChild(input);
            div.appendChild(label);
            optionsDiv.appendChild(div);

            input.addEventListener("change", handleStatusChange);
          }
        });
        showFlashMessage("Status Updated Succesfully!", "success");
      })
      .catch(err => {
        console.error("Update status error:", err);
        showFlashMessage("Failed to update status. Please refresh and try again.", "error");
      });
  }

  // === Sidebar Filtering ===
  document.querySelectorAll("#statusFilterSidebar a").forEach(link => {
    link.addEventListener("click", function (e) {
      e.preventDefault();
      document.querySelectorAll("#statusFilterSidebar a").forEach(l => l.classList.remove("active"));
      this.classList.add("active");
      currentStatusFilter = this.dataset.status.toLowerCase();
      updateTable();
    });
  });


  // === Search, Sort, Filter ===
  searchInput.addEventListener("input", () => {
    let val = searchInput.value
      .slice(0, 100)
      .replace(/[^\w\s\-]/g, '')
      .trim();
    searchInput.value = val;
    updateTable();
  });

  sortSelect.addEventListener("change", updateTable);
  filterCategory.addEventListener("change", updateTable);

  function updateTable() {
    const searchVal = searchInput.value.toLowerCase();
    const sortVal = sortSelect.value;
    const categoryVal = filterCategory.value;

    if (!VALID_CATEGORY_OPTIONS.includes(categoryVal)) {
      showFlashMessage("Invalid Category Selected. Resetting to all.", "error");
      categoryVal = "all";
      filterCategory.value = categoryVal;
    }
    if (!VALID_SORT_OPTIONS.includes(sortVal)) {
      showFlashMessage("Invalid Sort Selection. Resetting to default.", "error");
      sortVal = "id-asc";
      sortSelect.value = sortVal;
    }

    let filteredRows = originalRows.filter(row => {
      const title = row.children[1].textContent.toLowerCase();
      const categoryText = row.children[2]?.textContent.trim();
      const category = Object.keys(CATEGORY_MAPPING).find(
        key => CATEGORY_MAPPING[key] === categoryText
      ) || '';

      const status = row.dataset.status.toLowerCase();

      return (
        title.includes(searchVal) &&
        (categoryVal === "all" || category === categoryVal) &&
        (currentStatusFilter === "all" || status === currentStatusFilter)
      );
    });

    filteredRows.sort((a, b) => {
      const getId = row => +row.children[0].textContent;
      const getTitle = row => row.children[1].textContent;
      switch (sortVal) {
        case "id-asc": return getId(a) - getId(b);
        case "id-desc": return getId(b) - getId(a);
        case "desc-asc": return getTitle(a).localeCompare(getTitle(b));
        case "desc-desc": return getTitle(b).localeCompare(getTitle(a));
        default: return 0;
      }
    });

    tableBody.textContent = "";
    filteredRows.forEach(row => tableBody.appendChild(row));
    allRows.length = 0;
    allRows.push(...filteredRows);
    showPage(1);
  }

  // === View More Modal ===
  document.querySelectorAll(".animated-button").forEach(button => {
    button.addEventListener("click", async function () {
      const row = this.closest("tr");
      const { title = "", category = "", status = "", description = "", username = "", createdat = "", reportid } = row.dataset;

      if (!/^\d+$/.test(reportid)) return;

      const modalContent = document.getElementById("modalContent");
      modalContent.textContent = "";

      let imgContainer = document.getElementById("modalImageContainer") || document.createElement("div");
      imgContainer.id = "modalImageContainer";
      imgContainer.textContent = "";
      modalContent.prepend(imgContainer);

      try {
        const res = await fetch(`/admin/report_attachments/${reportid}`);
        if (!res.ok) throw new Error("Failed to load attachments");
        const attachments = await res.json();
        if (Array.isArray(attachments)) {
          attachments.forEach(att => {
            const img = document.createElement("img");
            img.src = `/uploads/${att.file_name}`;
            Object.assign(img.style, {
              maxHeight: "200px",
              borderRadius: "8px",
              objectFit: "contain",
              cursor: "pointer",
              marginRight: "1rem"
            });
            img.alt = "Report Attachment";
            imgContainer.appendChild(img);
          });
        }
      } catch (err) {
        console.error("Attachment load error:", err);
        showFlashMessage("Could not load attachments. Try again later.", "error");
      }

      const infoSection = document.createElement('div');
      infoSection.className = "info-section";

      [
        { label: 'Title', value: title },
        { label: 'Category', value: category },
        { label: 'Status', value: status.charAt(0).toUpperCase() + status.slice(1) },
        { label: 'Description', value: description },
        {label: 'Owner', value: username},
        {
        label: 'Created At',
        value: (() => {
          // Convert DB time (UTC) into proper ISO format
          const rawDate = new Date(createdat.replace(" ", "T") + "Z");

          // Format date like: July 9, 2025
          const dateOptions = { year: "numeric", month: "long", day: "numeric" };
          const formattedDate = rawDate.toLocaleDateString(undefined, dateOptions);

          // Format time like: 12:02 PM
          let hours = rawDate.getHours();
          const minutes = rawDate.getMinutes().toString().padStart(2, "0");
          const ampm = hours >= 12 ? "PM" : "AM";
          hours = hours % 12 || 12;
          const formattedTime = `${hours}:${minutes} ${ampm}`;

          return `${formattedDate} at ${formattedTime}`;
        })()
      }

      ].forEach(field => {
        const wrapper = document.createElement('div');
        wrapper.className = 'info-field';

        const lbl = document.createElement('div');
        lbl.className = 'info-label';
        lbl.textContent = field.label;

        const val = document.createElement('div');
        val.className = 'info-value';
        val.textContent = field.value;

        wrapper.appendChild(lbl);
        wrapper.appendChild(val);
        infoSection.appendChild(wrapper);
      });

      modalContent.appendChild(infoSection);
      new bootstrap.Modal(document.getElementById("reportDetailsModal")).show();
    });
  });

  // === Delete Flow ===
  document.querySelectorAll(".bin-button").forEach(button => {
    button.addEventListener("click", function () {
      selectedReportId = this.dataset.reportid;
      selectedRow = this.closest("tr");
      if (!/^\d+$/.test(selectedReportId)) return;
      new bootstrap.Modal(document.getElementById("deleteConfirmModal")).show();
    });
  });

  document.getElementById("confirmDeleteBtn").addEventListener("click", async function () {
    if (!/^\d+$/.test(selectedReportId)) return;
    try {
      const res = await fetch(`/admin/delete_report/${selectedReportId}`, {
        method: "DELETE",
        headers: { "X-CSRFToken": csrfToken }
      });

      if (res.ok) {
        selectedRow?.remove();
        bootstrap.Modal.getInstance(document.getElementById("deleteConfirmModal"))?.hide();
        showFlashMessage("Report Deleted Succesfully!", "success");
      } else {
        console.error("Failed to delete report");
        showFlashMessage("Failed to delete report. Please refresh and try again.", "error");
      }
    } catch (err) {
      console.error("Error deleting report", err);
      showFlashMessage("An error occurred while deleting the report.", "error");
    }
  });

  // === Pagination ===
  function showPage(page) {
    const totalPages = Math.ceil(allRows.length / rowsPerPage);
    page = Math.min(Math.max(page, 1), totalPages);

    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;

    allRows.forEach((row, i) => {
      row.style.display = i >= start && i < end ? "" : "none";
    });

    renderPaginationButtons(page);
  }

  function renderPaginationButtons(currentPage) {
    const totalPages = Math.ceil(allRows.length / rowsPerPage);
    const maxVisible = 5;
    paginationContainer.innerHTML = "";

    const ul = document.createElement("ul");
    ul.className = "pagination";

    const createPageItem = (text, page = null, disabled = false, active = false, isEllipsis = false, isIcon = false) => {
      const li = document.createElement("li");
      li.className = "page-item";
      if (disabled) li.classList.add("disabled");
      if (active) li.classList.add("active");
      if (isEllipsis) li.classList.add("disabled");

      const btn = document.createElement("button");
      btn.className = "page-link";

      if (isEllipsis) {
        btn.textContent = "...";
      } else if (isIcon) {
        const icon = document.createElement("i");
        icon.className = text;
        btn.appendChild(icon);
      } else {
        btn.textContent = text;
      }

      if (!disabled && page !== null && !isEllipsis) {
        btn.addEventListener("click", () => showPage(page));
      }

      li.appendChild(btn);
      return li;
    };

    ul.appendChild(createPageItem("fa-solid fa-chevron-left", currentPage - 1, currentPage === 1, false, false, true));

    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = startPage + maxVisible - 1;
    if (endPage > totalPages) {
      endPage = totalPages;
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
      ul.appendChild(createPageItem("1", 1));
      if (startPage > 2) ul.appendChild(createPageItem("...", null, true, false, true));
    }

    for (let i = startPage; i <= endPage; i++) {
      ul.appendChild(createPageItem(i, i, false, i === currentPage));
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) ul.appendChild(createPageItem("...", null, true, false, true));
      ul.appendChild(createPageItem(totalPages, totalPages));
    }

    ul.appendChild(createPageItem("fa-solid fa-chevron-right", currentPage + 1, currentPage === totalPages, false, false, true));

    paginationContainer.appendChild(ul);
  }

  showPage(1);
});