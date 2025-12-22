
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("addLecture").addEventListener("click", () => {

        let list = document.getElementById("lectureList");

        let card = document.createElement("div");
        card.classList.add("lecture-card");

        card.innerHTML = `
            <div class="lecture-header">
                <span class="lecture-title">New Lecture</span>
                <button class="delete-lecture-btn" onclick="this.closest('.lecture-card').remove()">✖</button>
            </div>

            <div class="lecture-body">

                <label>Lecture Title</label>
                <input type="text" class="lecture-title-input" placeholder="Enter lecture title">

                <label>Upload Video</label>
                <input type="file" accept="video/*" class="lecture-video-input">

                <label>Upload PDF</label>
                <input type="file" accept="application/pdf" class="lecture-file-input">

            </div>
        `;

        list.appendChild(card);
    });
});


function saveModule() {

    let fd = new FormData();

    fd.append("module_title", document.getElementById("moduleTitle").value);

    fd.append("description", document.getElementById("moduleDescription").value);

    const cards = document.querySelectorAll(".lecture-card");
    fd.append("lecture_count", cards.length);

    cards.forEach((card, i) => {

        fd.append(`lecture_title_${i}`, card.querySelector(".lecture-title-input").value || "");

        let videoInput = card.querySelector(".lecture-video-input");
        if (videoInput.files.length > 0) {
            fd.append(`lecture_video_${i}`, videoInput.files[0]);
        }

        let pdfInput = card.querySelector(".lecture-file-input");
        if (pdfInput.files.length > 0) {
            fd.append(`lecture_pdf_${i}`, pdfInput.files[0]);
        }
    });

    fetch(`${BASE_URL}/module/${MODULE_ID}/save/`, {
        method: "POST",
        body: fd
    })
    .then(async res => {
        let text = await res.text();
        try {
            return JSON.parse(text);
        } catch (err) {
            alert("Save failed – backend error.");
            return null;
        }
    })
    .then(data => {
        if (!data) return;

        alert("Module Saved!");
        goBack();
    })
    .catch(err => alert("Error: " + err));
}

function goBack() {
    window.location.href = `/instructor/courses/add/?course_id=${COURSE_ID}`;
}
