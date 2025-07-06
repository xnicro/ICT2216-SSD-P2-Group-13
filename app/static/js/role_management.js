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

function handleRoleChange(event) {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const label = event.currentTarget;
  const newRole = label.dataset.role;
  const selectContainer = label.closest(".select");
  const userId = selectContainer.dataset.userId;
  const selectedDiv = selectContainer.querySelector(".selected");
  const oldRole = selectedDiv.dataset.default.toLowerCase();

  fetch("/update_role", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken
    },
    body: JSON.stringify({
      user_id: userId,
      role: newRole
    })
  })
    .then(res => res.json())
    .then(result => {
      if (result.success) {
        const updatedRoleCap = newRole.charAt(0).toUpperCase() + newRole.slice(1);
        selectedDiv.textContent = ""; // Clear current content

        // Safely add the updated role text
        const textNode = document.createTextNode(updatedRoleCap);
        selectedDiv.appendChild(textNode);

        // Recreate and append the arrow SVG (safely)
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
        svg.setAttribute("height", "1em");
        svg.setAttribute("viewBox", "0 0 512 512");
        svg.classList.add("arrow");

        const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", "M233.4 406.6c12.5 12.5 32.8 12.5 45.3 0l192-192c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L256 338.7 86.6 169.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l192 192z");

        svg.appendChild(path);
        selectedDiv.appendChild(svg);

        selectedDiv.dataset.default = updatedRoleCap;

        showFlashMessage("Role updated successfully.", "success");

        // Update the role cell in the table
        const tableRow = selectContainer.closest("tr");
        const roleCell = tableRow.children[3];
        roleCell.textContent = updatedRoleCap;

        // Rebuild options safely
        const optionsContainer = selectContainer.querySelector(".options");
        optionsContainer.innerHTML = "";

        const allRoles = ["user", "admin"];
        allRoles.forEach(role => {
          if (role !== newRole) {
            const roleCap = role.charAt(0).toUpperCase() + role.slice(1);
            const id = `option-${role}-${userId}`;

            const div = document.createElement("div");
            div.title = id;

            const input = document.createElement("input");
            input.id = id;
            input.type = "radio";
            input.name = `option-${userId}`;

            const optionLabel = document.createElement("label");
            optionLabel.className = "option";
            optionLabel.setAttribute("for", id);
            optionLabel.dataset.role = role;
            optionLabel.textContent = roleCap;

            optionLabel.addEventListener("click", handleRoleChange);

            div.appendChild(input);
            div.appendChild(optionLabel);
            optionsContainer.appendChild(div);
          }
        });
      } else {
        console.error("Update failed:", result.error);
        showFlashMessage("Failed to update role. Please refresh and try again.", "error");
      }
    })
    .catch(err => {
      console.error("Request error:", err);
      showFlashMessage("Error updating role. Please refresh and try again.", "error");
    });
};


// Attach to existing options on initial load
document.querySelectorAll(".select .option").forEach(label => {
  label.addEventListener("click", handleRoleChange);
});

const tableBody = document.getElementById("rolesTableBody");
const originalRows = Array.from(tableBody.querySelectorAll("tr"));
const rowsPerPage = 7;
const allRows = [...originalRows];
const paginationContainer = document.getElementById("role-pagination");
let filteredRows = [...allRows]; 

// === Pagination ===
  function showPage(page) {
    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
    page = Math.min(Math.max(page, 1), totalPages);

    // Hide all rows first
    allRows.forEach(row => row.style.display = "none");

    const start = (page - 1) * rowsPerPage;
    const end = start + rowsPerPage;

    // Show only the filtered rows for current page
    filteredRows.slice(start, end).forEach(row => {
      row.style.display = "";
    });

    renderPaginationButtons(page);
  }


function renderPaginationButtons(currentPage) {
  const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
  paginationContainer.innerHTML = "";

  const ul = document.createElement("ul");
  ul.className = "pagination";

  const createPageItem = (text, page = null, disabled = false, active = false, isIcon = false) => {
    const li = document.createElement("li");
    li.className = "page-item";
    if (disabled) li.classList.add("disabled");
    if (active) li.classList.add("active");

    const btn = document.createElement("button");
    btn.className = "page-link";

    if (isIcon) {
      const icon = document.createElement("i");
      icon.className = text;
      btn.appendChild(icon);
    } else {
      btn.textContent = text;
    }

    if (!disabled && page !== null) {
      btn.addEventListener("click", () => showPage(page));
    }

    li.appendChild(btn);
    return li;
  };

  ul.appendChild(createPageItem("fa-solid fa-chevron-left", currentPage - 1, currentPage === 1, false, true));

  for (let i = 1; i <= totalPages; i++) {
    ul.appendChild(createPageItem(i, i, false, i === currentPage));
  }

  ul.appendChild(createPageItem("fa-solid fa-chevron-right", currentPage + 1, currentPage === totalPages, false, true));

  paginationContainer.appendChild(ul);
}

showPage(1);

document.addEventListener("DOMContentLoaded", function () {
  const searchInput = document.getElementById("searchInput");
  const roleFilter = document.getElementById("roleFilter");
  const tableRows = document.querySelectorAll("#rolesTableBody tr");
  const VALID_ROLES = ["", "user", "admin"];

  function filterTable() {
    let val = searchInput.value
      .slice(0, 100)
      .replace(/[^\w\s\-@.]/g, '')
      .trim();
    searchInput.value = val;

    let selectedRole = roleFilter.value.toLowerCase();
    if (!VALID_ROLES.includes(selectedRole)) {
      selectedRole = "";
      roleFilter.value = "";
    }

    const searchText = val.toLowerCase();

    filteredRows = [];

    allRows.forEach(row => {
      const username = row.children[1].textContent.toLowerCase();
      const email = row.children[2].textContent.toLowerCase();
      const role = row.children[3].textContent.toLowerCase();

      const matchesSearch = username.includes(searchText) || email.includes(searchText);
      const matchesRole = selectedRole === "" || role === selectedRole;

      if (matchesSearch && matchesRole) {
        filteredRows.push(row);
      }
    });

    showPage(1);  // Show first page of filtered results
  }


  searchInput.addEventListener("input", filterTable);
  roleFilter.addEventListener("change", filterTable);
});

