document.addEventListener("DOMContentLoaded", function () {
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
//   For modal in the future, remember to use scape html when injecting html from JS
});
