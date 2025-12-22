
function saveModule() {

    let fd = new FormData();

    fd.append("module_title", document.getElementById("moduleTitle").value);
    fd.append("description", document.getElementById("moduleDescription").value);

    const cards = document.querySelectorAll(".lecture-card");
    fd.append("lecture_count", cards.length);

    cards.forEach((card, i) => {

        let titleInput = card.querySelector(".lecture-title-input");
        let title = titleInput ? titleInput.value : "";
        fd.append(`lecture_title_${i}`, title);

        let videoInput = card.querySelector(".lecture-video-input");
        if (videoInput && videoInput.files.length > 0) {
            fd.append(`lecture_video_${i}`, videoInput.files[0]);
        } else {
            fd.append(`lecture_video_${i}`, "");
        }

        let pdfInput = card.querySelector(".lecture-file-input");
        if (pdfInput && pdfInput.files.length > 0) {
            fd.append(`lecture_pdf_${i}`, pdfInput.files[0]);
        } else {
            fd.append(`lecture_pdf_${i}`, "");
        }
    });

    fetch(`${BASE_URL}/module/${MODULE_ID}/save/`, {
        method: "POST",
        body: fd
    })
    .then(async (res) => {
        let text = await res.text();

        console.log("DEBUG RAW RESPONSE:", text);

        try {
            return JSON.parse(text);
        } catch (e) {
            alert("Save failed — Backend returned HTML. Check terminal.");
            return;
        }
    })
    .then(data => {
        if (!data) return;

        alert("Module saved successfully!");
        window.location.href = `${BASE_URL}/courses/${COURSE_ID}/edit/`;
    })
    .catch(err => {
        alert("Save failed: " + err);
    });
}

function deleteLecture(i) {
    const cards = document.querySelectorAll(".lecture-card");
    if (cards[i]) cards[i].remove();
}


document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("addLecture").addEventListener("click", () => {
        let list = document.getElementById("lectureList");

        let card = document.createElement("div");
        card.classList.add("lecture-card");

        card.innerHTML = `
            <div class="lecture-header">
                <span class="lecture-title">New Lecture</span>
                <button class="delete-lecture-btn" onclick="this.parentNode.parentNode.remove()">✖</button>
            </div>

            <div class="lecture-body">

                <label>Lecture Title</label>
                <input type="text" class="lecture-title-input" value="New Lecture">

                <label>Upload Video</label>
                <input type="file" accept="video/*" class="lecture-video-input">

                <label>Upload PDF</label>
                <input type="file" accept="application/pdf" class="lecture-file-input">

            </div>
        `;

        list.appendChild(card);
    });
});
