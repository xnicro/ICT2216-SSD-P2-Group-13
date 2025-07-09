// Format: July 1, 2025
const dateOptions = { year: "numeric", month: "long", day: "numeric" };
const formattedDate = rawDate.toLocaleDateString("en-US", dateOptions);

// Format time: 6:20 PM
let hours = rawDate.getHours();
const minutes = rawDate.getMinutes().toString().padStart(2, "0");
const ampm = hours >= 12 ? "PM" : "AM";
hours = hours % 12 || 12;
const formattedTime = `${hours}:${minutes} ${ampm}`;

document.getElementById("report-detail-date").textContent = formattedDate;
document.getElementById("report-detail-time").textContent = formattedTime;

const statusContainer = document.getElementById("report-detail-status");
statusContainer.textContent = report_detail_report.status_name;
const statusClass = `status-${report_detail_report.status_name.toLowerCase().replace(/\s+/g, '-')}`;
statusContainer.classList.add("status-badge", statusClass);

async function loadAttachments() {
    let imgContainer = document.getElementById("report-detail-images");
    try {
        const res = await fetch(`/report_attachments/${report_detail_report.report_id}`);
        if (!res.ok) throw new Error("Failed to load attachments");
        const attachments = await res.json();
        if (Array.isArray(attachments)) {
            attachments.forEach(att => {
                const img = document.createElement("img");
                img.src = `/uploads/${att.file_name}`;
                img.alt = "Report Attachment";
                imgContainer.appendChild(img);
            });
        }
    } catch (err) {
        console.error("Attachment load error:", err);
    }
}

loadAttachments();
