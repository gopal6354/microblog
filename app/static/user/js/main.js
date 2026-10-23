// =====================================
// EchoHub - Main JavaScript
// =====================================


// ================================
// Theme Toggle
// ================================

const html = document.documentElement;

const themeToggle = document.getElementById("theme-toggle");



// Load saved theme

const savedTheme = localStorage.getItem("theme") || "light";

html.setAttribute("data-theme", savedTheme);

updateTheme(savedTheme);



// Toggle theme

if (themeToggle) {

    themeToggle.addEventListener("click", function (e) {

        e.preventDefault();

        const currentTheme = html.getAttribute("data-theme");

        const newTheme =
            currentTheme === "dark"
                ? "light"
                : "dark";

        html.setAttribute("data-theme", newTheme);

        localStorage.setItem("theme", newTheme);

        updateTheme(newTheme);

    });

}



// Update icon and text

function updateTheme(theme) {

    if (!themeToggle) {

        return;

    }

    const icon = themeToggle.querySelector("i");

    const text = themeToggle.querySelector("span");



    if (theme === "dark") {

        icon.className = "bi bi-sun-fill";

        text.textContent = "Light Mode";

    }

    else {

        icon.className = "bi bi-moon-stars";

        text.textContent = "Dark Mode";

    }

}

//text area


const textarea = document.getElementById("post-content");

if (textarea) {

    textarea.addEventListener("input", function () {

        this.style.height = "auto";
        this.style.height = this.scrollHeight + "px";

        const counter = document.getElementById("character-count");

        if (counter) {
            counter.textContent = `${this.value.length} / 280`;
        }

    });

}
document.querySelectorAll(".like-btn").forEach(button => {

    button.addEventListener("click", async function () {

        const blogId = this.dataset.blogId;

        try {

            const response = await fetch(`/blog/${blogId}/like`, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                }
            });

            if (response.status === 401) {
                window.location.href = "/login";
                return;
            }

            if (response.status === 403) {
                window.location.href = "/admin-dashboard";
                return;
            }

            if (!response.ok) {
                alert("Something went wrong.");
                return;
            }

            const data = await response.json();

            const icon = this.querySelector("i");
            const count = this.querySelector("span");

            if (data.liked) {
                icon.classList.remove("bi-heart");
                icon.classList.add("bi-heart-fill", "text-danger");
            } else {
                icon.classList.remove("bi-heart-fill", "text-danger");
                icon.classList.add("bi-heart");
            }

            count.textContent = data.like_count;

        } catch (error) {
            console.error(error);
            alert("Unable to connect to the server.");
        }

    });

});
document.querySelectorAll(".report-btn").forEach(button => {

    button.addEventListener("click", function () {

        const blogId = this.dataset.blogId;

        document.getElementById("reportBlogId").value = blogId;

    });

});
// ================================
// Future JavaScript
// ================================

// Character Counter
// Post Like
// Follow Button
// Search
// Notifications
// Infinite Scroll
