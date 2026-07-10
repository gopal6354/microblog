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


// ================================
// Future JavaScript
// ================================

// Character Counter
// Post Like
// Follow Button
// Search
// Notifications
// Infinite Scroll