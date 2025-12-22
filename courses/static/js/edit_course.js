
let structure = [];
let courseId = COURSE_ID;
let dragType = null;

document.addEventListener("DOMContentLoaded", () => {
    loadExistingStructure();
    renderStructure();
});

function loadExistingStructure() {
    const cards = document.querySelectorAll(".builder-card");

    cards.forEach(card => {
        structure.push({
            type: card.dataset.type,
            title: "",  
            description: card.dataset.description || "",
            module_id: card.dataset.moduleId || null,
            quiz_id: card.dataset.quizId || null,
            assignment_id: card.dataset.assignmentId || null,
            liveclass_id: card.dataset.liveclassId || null,
            lectures: card.dataset.lectures ? JSON.parse(card.dataset.lectures) : []
        });
    });
}

function renderStructure() {
    const row = document.getElementById("topRow");
    row.innerHTML = "";

    let m = 1, q = 1, a = 1, l = 1;

    structure.forEach((item, index) => {
        if (item.type === "Module") item.title = `Module ${m++}`;
        else if (item.type === "Quiz") item.title = `Quiz ${q++}`;
        else if (item.type === "Assignment") item.title = `Assignment ${a++}`;
        else if (item.type === "Live Class") item.title = `Live Class ${l++}`;

        row.innerHTML += generateCardHTML(item, index);
    });

    row.innerHTML += `<div id="dropZone" class="drop-zone">+</div>`;

    enableReorder();
    enableAddDrop();
}

function generateCardHTML(item, index) {

    return `
        <div class="builder-card 
            ${item.type === "Module" ? "module-card" : ""}
            ${item.type === "Quiz" ? "quiz-card" : ""}
            ${item.type === "Assignment" ? "assignment-card" : ""}
            ${item.type === "Live Class" ? "liveclass-card" : ""}
        " draggable="true" data-index="${index}">
        
            <div class="card-title">${item.title}</div>

            <div class="card-actions">
                ${item.type === "Module" ?
                    `<button onclick="openModule(${index})" class="open-module-btn">Edit</button>` 
                : ""}
                <button onclick="deleteBlock(${index})" class="delete-module-btn">✖</button>
            </div>
        </div>
    `;
}


function enableAddDrop() {
    const oldZone = document.getElementById("dropZone");
    const dropZone = oldZone.cloneNode(true);
    oldZone.replaceWith(dropZone);

    document.querySelectorAll(".draggable-btn").forEach(btn => {
        btn.addEventListener("dragstart", () => dragType = btn.dataset.type);
        btn.addEventListener("dragend", () => dragType = null);
    });

    dropZone.addEventListener("dragover", e => e.preventDefault());

    dropZone.addEventListener("drop", () => {
        if (!dragType) return;

        structure.push({
            type: dragType,
            title: "",
            description: "",
            module_id: null,
            quiz_id: null,
            assignment_id: null,
            liveclass_id: null,
            lectures: []
        });

        renderStructure();
    });
}

function enableReorder() {
    const cards = document.querySelectorAll(".builder-card");

    cards.forEach(card => {
        card.addEventListener("dragstart", e => {
            e.dataTransfer.setData("oldIndex", card.dataset.index);
        });

        card.addEventListener("dragover", e => e.preventDefault());

        card.addEventListener("drop", e => {
            e.preventDefault();

            const oldIndex = parseInt(e.dataTransfer.getData("oldIndex"));
            const newIndex = parseInt(card.dataset.index);

            const moved = structure.splice(oldIndex, 1)[0];
            structure.splice(newIndex, 0, moved);

            renderStructure();
        });
    });
}


function openModule(index) {
    const item = structure[index];

    if (!item.module_id) {
        fetch(`${BASE_URL}/module/create/`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ course_id: COURSE_ID })
        })
        .then(r => r.json())
        .then(data => {
            structure[index].module_id = data.module_id;

            saveCourse(() => {
                window.location.href =
                    `${BASE_URL}/courses/${COURSE_ID}/module/${data.module_id}/edit/`;
            });
        });

        return;
    }

    saveCourse(() => {
        window.location.href =
            `${BASE_URL}/courses/${COURSE_ID}/module/${item.module_id}/edit/`;
    });
}

function deleteBlock(index) {
    if (!confirm("Delete this item?")) return;

    structure.splice(index, 1);
    renderStructure();
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
        headers: {"Content-Type": "application/json"},
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
    if (!courseId) return alert("Please save first!");
    saveCourse(() => {
        window.location.href = `${BASE_URL}/publish/${courseId}/`;
    });
}

