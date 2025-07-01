function handleRoleChange(event) {
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
        alert("Failed to update role.");
      }
    })
    .catch(err => {
      console.error("Request error:", err);
      alert("Error updating role.");
    });
}


// Attach to existing options on initial load
document.querySelectorAll(".select .option").forEach(label => {
  label.addEventListener("click", handleRoleChange);
});
