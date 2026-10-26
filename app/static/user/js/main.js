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

const imageUploadButton = document.getElementById("image-upload-button");
const postImageInput = document.getElementById("post-image");
const selectedImageName = document.getElementById("selected-image-name");

if (imageUploadButton && postImageInput) {
    imageUploadButton.addEventListener("click", function () {
        postImageInput.click();
    });

    postImageInput.addEventListener("change", function () {
        if (selectedImageName) {
            selectedImageName.textContent = this.files.length
                ? this.files[0].name
                : "";
        }
    });
}

const emojiPickerButton = document.getElementById("emoji-picker-button");
const emojiPicker = document.getElementById("emoji-picker");

if (emojiPickerButton && emojiPicker && textarea) {
    emojiPickerButton.addEventListener("click", function () {
        emojiPicker.hidden = !emojiPicker.hidden;
        this.setAttribute("aria-expanded", String(!emojiPicker.hidden));
    });

    emojiPicker.querySelectorAll("[data-emoji-code]").forEach(button => {
        button.addEventListener("click", function () {
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const emoji = this.dataset.emojiCode
                .split("-")
                .map(codePoint => String.fromCodePoint(parseInt(codePoint, 16)))
                .join("");
            textarea.setRangeText(emoji, start, end, "end");
            textarea.dispatchEvent(new Event("input", { bubbles: true }));
            textarea.focus();
        });
    });
}

const locationButton = document.getElementById("location-button");
const locationInput = document.getElementById("post-location");
const locationStatus = document.getElementById("post-location-status");

async function reverseGeocode(latitude, longitude) {
    const query = new URLSearchParams({
        format: "jsonv2",
        lat: latitude,
        lon: longitude,
        zoom: "14",
        addressdetails: "1"
    });
    const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?${query}`,
        { headers: { Accept: "application/json" } }
    );
    if (!response.ok) throw new Error("Reverse geocoding failed");

    const result = await response.json();
    const address = result.address || {};
    const city = address.city || address.town || address.village || address.municipality;
    const region = address.state || address.county;
    const placeName = [city, region].filter(Boolean).join(", ")
        || result.name
        || result.display_name?.split(",").slice(0, 2).join(", ");

    if (!placeName) throw new Error("No place name found");
    return placeName;
}

if (locationButton && locationInput && locationStatus) {
    const locationForm = locationButton.form;
    const locationSubmitButton = locationForm?.querySelector('[type="submit"]');
    const locationClearButton = document.getElementById("location-clear-button");
    let locationLookupPending = false;

    // Keep the post from being submitted before the place name arrives.
    function setLocationPending(pending) {
        locationLookupPending = pending;
        locationButton.disabled = pending;
        if (locationSubmitButton) locationSubmitButton.disabled = pending;
    }

    function setLocation(placeName, message) {
        locationInput.value = placeName;
        locationStatus.textContent = message;
        if (locationClearButton) locationClearButton.hidden = !placeName;
    }

    if (locationForm) {
        locationForm.addEventListener("submit", function (event) {
            if (locationLookupPending) event.preventDefault();
        });
    }

    if (locationClearButton) {
        locationClearButton.addEventListener("click", function () {
            setLocation("", "");
        });
    }

    locationButton.addEventListener("click", function () {
        if (!window.isSecureContext) {
            locationStatus.textContent = "Location needs HTTPS or localhost.";
            return;
        }
        if (!navigator.geolocation) {
            locationStatus.textContent = "Location is not available in this browser.";
            return;
        }

        setLocationPending(true);
        locationStatus.textContent = "Sharing your coordinates with OpenStreetMap to find a place name...";
        navigator.geolocation.getCurrentPosition(
            async position => {
                const { latitude, longitude } = position.coords;
                try {
                    const placeName = await reverseGeocode(latitude, longitude);
                    setLocation(placeName, `Location added: ${placeName}`);
                } catch (error) {
                    setLocation("", "Couldn't find a place name. Please try again.");
                } finally {
                    setLocationPending(false);
                }
            },
            () => {
                setLocation(locationInput.value, "Location was unavailable or permission was denied.");
                setLocationPending(false);
            },
            { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
        );
    });
}

document.querySelectorAll(".post-location[data-blog-id]").forEach(locationLine => {
    if (locationLine.dataset.canEdit !== "true") return;

    const coordinateMatch = locationLine.dataset.location.match(
        /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/
    );
    if (!coordinateMatch) return;

    const resolveButton = document.createElement("button");
    resolveButton.type = "button";
    resolveButton.className = "resolve-location-button";
    resolveButton.textContent = "Show place name";
    locationLine.append(" ", resolveButton);

    const status = document.createElement("span");
    status.className = "resolve-location-status";
    locationLine.append(" ", status);

    resolveButton.addEventListener("click", async function () {
        this.disabled = true;
        status.textContent = "Looking up place...";
        try {
            const placeName = await reverseGeocode(coordinateMatch[1], coordinateMatch[2]);
            const response = await fetch(`/blog/${locationLine.dataset.blogId}/location`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({ location: placeName })
            });
            if (!response.ok) throw new Error("Could not save the place name");

            const result = await response.json();
            locationLine.querySelector(".post-location-name").textContent = result.location;
            locationLine.dataset.location = result.location;
            this.remove();
            status.remove();
        } catch (error) {
            status.textContent = "Could not resolve location. Try again.";
            this.disabled = false;
        }
    });
});

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
// Comments
// ================================

// redirects to login/admin for auth failures; returns null when handled
async function postAction(url, body) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body
    });

    if (response.status === 401) {
        window.location.href = "/login";
        return null;
    }

    const data = await response.json().catch(() => ({}));

    // the admin guard answers 403 without our own "message" field
    if (response.status === 403 && !data.message) {
        window.location.href = "/admin-dashboard";
        return null;
    }

    if (!response.ok) throw new Error(data.message || "Something went wrong.");
    return data;
}

function updateCommentCount(postCard, count) {
    const counter = postCard.querySelector(".comment-count");
    if (counter) counter.textContent = count;
}

document.querySelectorAll(".comment-toggle-btn").forEach(button => {
    button.addEventListener("click", function () {
        const section = document.getElementById(this.getAttribute("aria-controls"));
        section.hidden = !section.hidden;
        this.setAttribute("aria-expanded", String(!section.hidden));

        if (!section.hidden) {
            section.querySelector(".comment-form input")?.focus();
        }
    });
});

document.querySelectorAll(".comment-form").forEach(form => {
    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const input = this.querySelector("input[name='content']");
        const submit = this.querySelector("button[type='submit']");
        const content = input.value.trim();
        if (!content) return;

        submit.disabled = true;
        try {
            const data = await postAction(
                `/blog/${this.dataset.blogId}/comment`,
                new URLSearchParams({ content })
            );
            if (!data) return;

            // server-rendered partial, content is already escaped by Jinja
            const list = this.closest(".post-comments").querySelector(".comment-list");
            list.insertAdjacentHTML("beforeend", data.comment_html);
            updateCommentCount(this.closest(".post-card"), data.comment_count);
            input.value = "";
        } catch (error) {
            alert(error.message);
        } finally {
            submit.disabled = false;
        }
    });
});

// a comment notification links to /#post-<id>; open that post's comments
const linkedPost = window.location.hash.match(/^#post-\d+$/)
    && document.querySelector(window.location.hash);
if (linkedPost) {
    const toggle = linkedPost.querySelector(".comment-toggle-btn");
    if (toggle && toggle.getAttribute("aria-expanded") !== "true") toggle.click();
    linkedPost.scrollIntoView({ block: "start" });
}

// delegated so freshly added comments can be deleted too
document.addEventListener("click", async function (e) {
    const button = e.target.closest(".comment-delete-btn");
    if (!button || !confirm("Delete this comment?")) return;

    button.disabled = true;
    try {
        const data = await postAction(`/comment/${button.dataset.commentId}/delete`);
        if (!data) return;

        const postCard = button.closest(".post-card");
        button.closest(".comment-item").remove();
        updateCommentCount(postCard, data.comment_count);
    } catch (error) {
        alert(error.message);
        button.disabled = false;
    }
});

// ================================
// Follow Button
// ================================

document.querySelectorAll(".follow-btn").forEach(button => {
    button.addEventListener("click", async function () {
        const userId = this.dataset.userId;

        this.disabled = true;
        try {
            const data = await postAction(`/user/${userId}/follow`);
            if (!data) return;

            // keep every button for this user in sync (sidebar, profile, lists)
            document.querySelectorAll(`.follow-btn[data-user-id="${userId}"]`).forEach(btn => {
                btn.dataset.following = String(data.following);
                btn.textContent = data.following ? "Following" : "Follow";
                btn.classList.toggle("btn-primary", !data.following);
                btn.classList.toggle("btn-outline-primary", data.following);
            });

            document.querySelectorAll(`[data-follower-count-for="${userId}"]`).forEach(el => {
                el.textContent = data.follower_count;
            });
        } catch (error) {
            alert(error.message);
        } finally {
            this.disabled = false;
        }
    });
});

// ================================
// Future JavaScript
// ================================

// Search
// Notifications
// Infinite Scroll
