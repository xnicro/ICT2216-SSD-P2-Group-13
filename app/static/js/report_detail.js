console.log(rawDate);
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
let imgContainer = document.getElementById("report-detail-images");
//Load Images
try {
    const res = await fetch(`/report_attachments/${reportid}`);
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
    showFlashMessage("Could not load attachments. Try again later.", "error");
}