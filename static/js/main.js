// =======================
// MENU TOGGLE
// =======================
document.addEventListener("DOMContentLoaded", () => {
  const menuToggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");

  if (menuToggle && sidebar && overlay) {
    menuToggle.addEventListener("click", () => {
      sidebar.classList.toggle("active");
      overlay.classList.toggle("show");
    });

    overlay.addEventListener("click", () => {
      sidebar.classList.remove("active");
      overlay.classList.remove("show");
    });
  }
});

// =======================
// TASK MODAL LOGIC
// =======================

let editingCard = null;

function openModal(card = null) {
  const modal = document.getElementById("taskModal");
  modal.classList.add("show");

  if (card) {
    editingCard = card;
    document.getElementById("taskTitle").value =
      card.querySelector("h4").innerText;
    document.getElementById("taskDesc").value =
      card.querySelector("p").innerText;
    document.getElementById("taskStatus").value =
      card.querySelector(".tag").innerText.toLowerCase();
  } else {
    editingCard = null;
    clearForm();
  }
}

function closeModal() {
  document.getElementById("taskModal").classList.remove("show");
  clearForm();
}

function clearForm() {
  document.getElementById("taskTitle").value = "";
  document.getElementById("taskDesc").value = "";
  document.getElementById("taskStatus").value = "todo";
}

// =======================
// SAVE TASK
// =======================
function saveTask() {
  if (!activeCard) return;

  const title = document.getElementById("taskTitle").value;
  const desc = document.getElementById("taskDesc").value;
  const status = document.getElementById("taskStatus").value;

  fetch("/update-task", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      id: activeCard.dataset.id,
      title: title,
      description: desc,
      status: status
    })
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      // Update UI
      activeCard.querySelector("h4").innerText = title;
      activeCard.querySelector("p").innerText = desc;
      activeCard.querySelector(".tag").innerText = status;
      activeCard.dataset.status = status;

      const col = document.querySelector(`.column[data-status="${status}"]`);
      col.appendChild(activeCard);

      closeModal();
    } else {
      alert("Update failed");
    }
  });
}

const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");

menuToggle.addEventListener("click", () => {
  sidebar.classList.toggle("show");
  overlay.classList.toggle("show");
  menuToggle.classList.toggle("sidebar-open");
});

overlay.addEventListener("click", () => {
  sidebar.classList.remove("show");
  overlay.classList.remove("show");
  menuToggle.classList.remove("sidebar-open");
});


// =======================
// EDIT + DELETE
// =======================
function editTask(btn) {
  const card = btn.closest(".card");
  openModal(card);
}

function deleteTask(btn) {
  if (confirm("Delete this task?")) {
    btn.closest(".card").remove();
  }
}
