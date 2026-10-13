document.addEventListener("DOMContentLoaded", function () {
    // ---------- Tabs ----------
    const tabButtons = document.querySelectorAll(".tab-link");
    const panels = document.querySelectorAll(".tab-panel");

    function showTab(name) {
        panels.forEach(p => { p.hidden = p.id !== "tab-" + name; });
        tabButtons.forEach(b => {
            const active = b.dataset.tab === name;
            b.classList.toggle("active", active);
            b.setAttribute("aria-selected", active ? "true" : "false");
        });
    }

    tabButtons.forEach(b => b.addEventListener("click", () => showTab(b.dataset.tab)));

    // "Analyze Project" nav link should reveal the details tab first
    const navLink = document.querySelector(".nav-link");
    if (navLink) {
        navLink.addEventListener("click", () => showTab("details"));
    }

    // ---------- Form validation ----------
    const form = document.getElementById("projectForm");
    if (!form) return;
    const button = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", function (event) {
        const title = document.getElementById("title").value.trim();
        const code = document.getElementById("code").value;

        if (!title) {
            event.preventDefault();
            alert("Please enter a project title.");
            return;
        }
        if (code.length > 100000) {
            event.preventDefault();
            alert("Source code must be below 100,000 characters.");
            return;
        }
        button.disabled = true;
        button.textContent = "Analyzing...";
    });

    // Re-enable the button if the user returns via the back button
    window.addEventListener("pageshow", function () {
        button.disabled = false;
        button.textContent = "Analyze Now →";
    });
});
