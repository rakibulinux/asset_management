function keepAssetManagementOpen() {
    const links = document.querySelectorAll("li > a");

    links.forEach((link) => {
        const text = link.textContent.replace(/\s+/g, " ").trim();

        if (text.includes("Asset Management")) {
            const li = link.parentElement;
            const submenu = li.querySelector(":scope > ul.desktop-list-menu");
            const arrow = link.querySelector(".sub-menu-arrow");

            li.classList.add("active");

            if (submenu) {
                submenu.style.display = "block";
                submenu.style.height = "auto";
                submenu.style.maxHeight = "none";
                submenu.style.opacity = "1";
                submenu.style.visibility = "visible";
            }

            if (arrow) {
                arrow.style.transform = "rotate(180deg)";
            }
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(keepAssetManagementOpen, 1000);
});