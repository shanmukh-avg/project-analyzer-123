document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("projectForm");
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
});