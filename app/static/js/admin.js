document.addEventListener("DOMContentLoaded", function () {
  const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
// Update status part
  document.querySelectorAll(".options input[type='radio']").forEach(function (radio) {
    radio.addEventListener("change", function () {
      const reportId = this.name.split('-')[1];
      const selectedLabel = document.querySelector(`label[for='${this.id}']`);
      const statusText = selectedLabel.dataset.txt;
      const statusId = parseInt(this.id.split('-')[1]);

      const selectedDiv = this.closest(".select").querySelector(".selected");
      selectedDiv.textContent = statusText;

      fetch("/update_status", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Use CSRF token 
          "X-CSRFToken": csrfToken
        },
        body: JSON.stringify({
          report_id: reportId,
          status_id: statusId
        })
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          console.log("Status updated");
          const row = selectedDiv.closest("tr");
          const badge = row.querySelector(".status-badge");
          badge.textContent = statusText;
          badge.className = "status-badge status-" + statusText.toLowerCase();

          const optionsDiv = row.querySelector(".options");
          optionsDiv.textContent  = ""; 

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

              // Add event listener for new radio input
              input.addEventListener("change", arguments.callee); 
            }
          });

        } else {
          alert("Failed to update status");
        }
      });
    });
  });

//   For side bar filtering
  const sidebarLinks = document.querySelectorAll("#statusFilterSidebar a");
  const tableRows = document.querySelectorAll("#reportsTableBody tr");

  sidebarLinks.forEach(link => {
    link.addEventListener("click", function(event) {
      event.preventDefault();

      sidebarLinks.forEach(l => l.classList.remove("active"));
      // Add active class to the clicked link
      this.classList.add("active");

      const filterStatus = this.dataset.status.toLowerCase();

      tableRows.forEach(row => {
        const rowStatus = row.dataset.status.toLowerCase();

        // Show row if filter is 'all' or matches row status, else hide
        if (filterStatus === "all" || rowStatus === filterStatus) {
          row.style.display = "";
        } else {
          row.style.display = "none";
        }
      });
    });
  });

//   For search, sort, filter functionalities
  const searchInput = document.getElementById("searchInput");
  const sortSelect = document.getElementById("sortSelect");
  const filterCategory = document.getElementById("filterCategory");
  const tableBody = document.getElementById("reportsTableBody");

  // Get original data from table on load
  const originalRows = Array.from(tableBody.querySelectorAll("tr"));

  // Event listeners
  // Sanitisation for inputs    
  searchInput.addEventListener("input", () => {
    let val = searchInput.value;
    val = val.slice(0, 100); // max length
    val = val.replace(/[^\w\s\-]/g, ''); // only allow alphanumeric, spaces
    searchInput.value = val;
    updateTable();
    });
  sortSelect.addEventListener("change", updateTable);
  filterCategory.addEventListener("change", updateTable);

  function updateTable() {
    const searchValue = searchInput.value.toLowerCase();
    const sortValue = sortSelect.value;
    const categoryValue = filterCategory.value;

    let filteredRows = originalRows.filter((row) => {
      const title = row.children[1].textContent.toLowerCase();
      const category = row.children[2].textContent.toLowerCase();

      const matchesSearch = title.includes(searchValue);
      const matchesCategory =
        categoryValue === "all" ||
        category.replace(/\s+/g, "_") === categoryValue;


      return matchesSearch && matchesCategory;
    });

    // Sorting
    filteredRows.sort((a, b) => {
      if (sortValue === "id-asc") {
        return +a.children[0].textContent - +b.children[0].textContent;
      } else if (sortValue === "id-desc") {
        return +b.children[0].textContent - +a.children[0].textContent;
      } else if (sortValue === "desc-asc") {
        return a.children[1].textContent.localeCompare(b.children[1].textContent);
      } else if (sortValue === "desc-desc") {
        return b.children[1].textContent.localeCompare(a.children[1].textContent);
      }
    });

    // Clear and repopulate the table
    tableBody.textContent = "";
    filteredRows.forEach((row) => tableBody.appendChild(row));
  }
  
// More Details modal
document.querySelectorAll(".animated-button").forEach(button => {
  button.addEventListener("click", async function () {
    const row = button.closest("tr");

    // Get data attributes
    const title = row.dataset.title || '';
    const category = row.dataset.category || '';
    const status = row.dataset.status || '';
    const description = row.dataset.description || '';
    const createdAt = row.dataset.createdat || '';
    const reportId = row.dataset.reportid;

    if (!reportId) {
      console.warn("No report ID found for this row.");
      return;
    }

    const modalContent = document.getElementById("modalContent");
    modalContent.innerHTML = ''; 

    // Create or clear the image container
    let imgContainer = document.getElementById('modalImageContainer');
    if (!imgContainer) {
      imgContainer = document.createElement('div');
      imgContainer.id = 'modalImageContainer';
      modalContent.prepend(imgContainer); // Insert above all content
    } else {
      imgContainer.innerHTML = '';
      modalContent.prepend(imgContainer);
    }

    // Fetch attachments
    try {
      const res = await fetch(`/admin/report_attachments/${reportId}`);
      const attachments = await res.json();

      if (!Array.isArray(attachments)) {
        console.error("Attachments response is not an array");
        return;
      }

      if (attachments.length > 0) {
        attachments.forEach(att => {
          const fileName = att.file_name;
          const imageUrl = `/uploads/${fileName}`;

          const img = document.createElement('img');
          img.src = imageUrl;
          img.alt = 'Report Attachment';
          img.style.maxHeight = "200px";
          img.style.borderRadius = "8px";
          img.style.objectFit = "contain";
          img.style.cursor = "pointer";
          img.style.marginRight = "1rem";

          imgContainer.appendChild(img);
        });
      }
    } catch (err) {
      console.error("Failed to load attachment image");
    }

    // Show text fields below the images
    const fields = [
      { label: 'Title', value: title },
      { label: 'Category', value: category },
      { label: 'Status', value: status.charAt(0).toUpperCase() + status.slice(1) },
      { label: 'Description', value: description },
      { label: 'Created At', value: createdAt }
    ];

    const infoSection = document.createElement('div');
    infoSection.className = "info-section"; // Add a container

    fields.forEach(field => {
      const fieldContainer = document.createElement('div');
      fieldContainer.className = 'info-field';

      const label = document.createElement('div');
      label.className = 'info-label';
      label.textContent = field.label;

      const value = document.createElement('div');
      value.className = 'info-value';
      value.textContent = field.value;

      fieldContainer.appendChild(label);
      fieldContainer.appendChild(value);
      infoSection.appendChild(fieldContainer);
    });

    modalContent.appendChild(infoSection);

    // Show modal
    const bootstrapModal = new bootstrap.Modal(document.getElementById("reportDetailsModal"));
    bootstrapModal.show();
  });
});

// Delete Functions 
let selectedReportId = null;
let selectedRow = null;

document.querySelectorAll(".bin-button").forEach(button => {
  button.addEventListener("click", function () {
    selectedReportId = this.dataset.reportid;
    selectedRow = this.closest("tr");

    const confirmModal = new bootstrap.Modal(document.getElementById("deleteConfirmModal"));
    confirmModal.show();
  });
});

document.getElementById("confirmDeleteBtn").addEventListener("click", async function () {
  if (!selectedReportId) return;

  try {
    const res = await fetch(`/admin/delete_report/${selectedReportId}`, {
      method: "DELETE",
      headers: {
        // Use CSRF token 
        "X-CSRFToken": csrfToken
      }
    });

    if (res.ok) {
      // Remove row from DOM
      if (selectedRow) selectedRow.remove();

      // Close modal
      bootstrap.Modal.getInstance(document.getElementById("deleteConfirmModal")).hide();
    } else {
      console.error("Failed to delete report");
    }
  } catch (err) {
    console.error("Error deleting report");
  }
});

});
