
let structure = PRELOAD || [];
let courseId = COURSE_ID !== "null" ? COURSE_ID : null;
let dragType = null;


document.addEventListener("DOMContentLoaded", () => {
    renderStructure();
    enableDragMenu();
});


function renderStructure() {
    const row = document.getElementById("topRow");
    row.innerHTML = "";

    let moduleNum = 1, quizNum = 1, assignNum = 1, liveNum = 1;

    structure.forEach((item, index) => {

        if (item.type === "Module") item.display_title = `Module ${moduleNum++}`;
        if (item.type === "Quiz") item.display_title = `Quiz ${quizNum++}`;
        if (item.type === "Assignment") item.display_title = `Assignment ${assignNum++}`;
        if (item.type === "Live Class") item.display_title = `Live Class ${liveNum++}`;

        row.innerHTML += blockHTML(item, index);
    });

    row.innerHTML += `<div id="dropZone" class="drop-zone">+</div>`;

    enableDropZone();
    enableReorder();
}

function blockHTML(item, index) {
    let colorClass = "";

    if (item.type === "Module") colorClass = "module-card";
    if (item.type === "Quiz") colorClass = "quiz-card";
    if (item.type === "Assignment") colorClass = "assignment-card";
    if (item.type === "Live Class") colorClass = "liveclass-card";

    return `
        <div class="builder-card ${colorClass}" draggable="true" data-index="${index}">
            
            <div class="card-title">${item.display_title}</div>

            <div class="card-actions">
                ${item.type === "Module" ? 
                    `<button class="open-module-btn" onclick="openModule(${index})">Open</button>` 
                : ""}
                <button class="delete-module-btn" onclick="deleteModule(${index})">✖</button>
            </div>
        </div>
    `;
}


function enableDragMenu() {
    document.querySelectorAll(".draggable-btn").forEach(btn => {
        btn.addEventListener("dragstart", () => dragType = btn.dataset.type);
        btn.addEventListener("dragend", () => dragType = null);
    });
}

function enableDropZone() {
    const drop = document.getElementById("dropZone");

    drop.addEventListener("dragover", e => e.preventDefault());

    drop.addEventListener("drop", () => {
        if (!dragType) return;

        structure.push({
            type: dragType,
            title: "",
            module_id: null,
            lectures: []
        });

        renderStructure();
    });
}


function enableReorder() {
    document.querySelectorAll(".builder-card").forEach(card => {

        card.addEventListener("dragstart", e => {
            e.dataTransfer.setData("oldIndex", card.dataset.index);
        });

        card.addEventListener("dragover", e => e.preventDefault());

        card.addEventListener("drop", e => {
            const oldIndex = parseInt(e.dataTransfer.getData("oldIndex"));
            const newIndex = parseInt(card.dataset.index);
            const item = structure.splice(oldIndex, 1)[0];
            structure.splice(newIndex, 0, item);

            renderStructure();
        });
    });
}

function deleteModule(index) {
    const item = structure[index];

    if (!confirm("Delete this item permanently?")) return;

    if (item.type === "Module" && item.module_id) {

        fetch(`/instructor/module/${item.module_id}/delete/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        })
        .then(r => r.json())
        .then(data => {
            structure = data.structure;
            renderStructure();
        });

        return;
    }
    structure.splice(index, 1);
    renderStructure();
}

function openModule(index) {
    const item = structure[index];

    if (!courseId) {
        alert("Please save the course first!");
        return;
    }

    if (!item.module_id) {

        fetch(`/instructor/module/create/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ course_id: courseId })
        })
        .then(r => r.json())
        .then(data => {

            structure[index].module_id = data.module_id;

            saveCourse(() => {
                window.location.href =
                    `/instructor/courses/${courseId}/module/${data.module_id}/module_add/`;
            });
        });

        return;
    }

    saveCourse(() => {
        window.location.href =
            `/instructor/courses/${courseId}/module/${item.module_id}/module_add/`;
    });
}


function saveCourse(callback = null) {

    const payload = {
        course_id: courseId,
        title: document.getElementById("courseTitle").value,
        description: document.getElementById("courseDescription").value,
        price: document.getElementById("coursePrice").value,
        category: document.getElementById("courseCategory").value,
        structure: structure
    };

    fetch(`/instructor/save/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(r => r.json())
    .then(data => {
        courseId = data.course_id;
        structure = data.structure;

        if (callback) callback();
        else alert("Course Saved!");
    });
}

function publishCourse() {
    if (!courseId) return alert("Please save before publishing!");

    saveCourse(() => {
        window.location.href = `/instructor/publish/${courseId}/`;
    });
}
