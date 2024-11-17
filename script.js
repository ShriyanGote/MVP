document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector('form');
    const loadingScreen = document.getElementById("loading-screen");
    const content = document.querySelector('.container');

    form.addEventListener('submit', function () {
        // Show loading screen and allow form submission
        loadingScreen.style.display = "flex";
        content.style.display = "none";
    });
});

