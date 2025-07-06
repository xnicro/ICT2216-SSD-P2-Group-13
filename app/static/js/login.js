document.addEventListener('DOMContentLoaded', function () {
    // Auto-hide flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Read retryAfter from data attribute
    const body = document.querySelector('body');
    const retryAfterRaw = body.getAttribute('data-retry-after');
    const retryAfter = parseInt(retryAfterRaw, 10);

    if (!isNaN(retryAfter) && retryAfter > 0) {
        console.log(`Rate limit active. Enabling form in ${retryAfter} seconds.`);
        setTimeout(() => {
            document.getElementById("username").disabled = false;
            document.getElementById("password").disabled = false;

            const btn = document.querySelector("button[type='submit']");
            btn.disabled = false;
            btn.style.backgroundColor = "";

            document.querySelector("form#login-form").onsubmit = null;
        }, retryAfter * 1000);
    }
});
