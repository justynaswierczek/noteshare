document.addEventListener("DOMContentLoaded", function () {
    let noteToDelete = null;

    function confirmDelete(noteId) {
        let overlay = document.createElement("div");
        overlay.className = "custom-overlay";

        let dialog = document.createElement("div");
        dialog.className = "custom-dialog";
        dialog.innerHTML = `
        <p class="modal-text">Czy na pewno chcesz usunąć tę notatkę?</p>
        <div class="modal-footer">
            <button id="cancelBtn">Anuluj</button>
            <button id="confirmBtn">Usuń</button>
        </div>
    `;

        overlay.appendChild(dialog);
        document.body.appendChild(overlay);

        // Obsługa "Anuluj"
        document.getElementById("cancelBtn").addEventListener("click", function (event) {
            event.stopPropagation();
            document.body.removeChild(overlay);
        });

        // Obsługa "Usuń"
        document.getElementById("confirmBtn").addEventListener("click", function (event) {
            event.stopPropagation();
            deleteNote(noteId);
            document.body.removeChild(overlay);
        });

        // Zamknięcie po kliknięciu poza oknem
        overlay.addEventListener("click", function () {
            document.body.removeChild(overlay);
        });

        // Blokowanie zamykania po kliknięciu w modal
        dialog.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    }

    function deleteNote(noteId) {
        fetch("/delete-note", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ noteId }),
        }).then((_res) => {
            window.location.href = "/";
        });
    }

    // ⚠️ NOWA POPRAWKA: Dynamiczne przypisanie eventów do przycisków usuwania
    document.querySelectorAll(".delete-note-btn").forEach((button) => {
        button.addEventListener("click", function () {
            let noteId = this.getAttribute("data-id");
            if (noteId) {
                confirmDelete(noteId);
            } else {
                console.error("Brak ID notatki.");
            }
        });
    });
});