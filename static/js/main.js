document.addEventListener("DOMContentLoaded", () => {
    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.getElementById("navLinks");
  
    if (!menuToggle || !navLinks) return;
  
    // Toggle menu open/close
    menuToggle.addEventListener("click", () => {
      menuToggle.classList.toggle("active");
      navLinks.classList.toggle("active");
    });
  
    // Close menu when clicking outside
    document.addEventListener("click", (e) => {
      if (
        !menuToggle.contains(e.target) &&
        !navLinks.contains(e.target)
      ) {
        menuToggle.classList.remove("active");
        navLinks.classList.remove("active");
      }
    });
  
    // Close menu when clicking a nav link
    document.querySelectorAll(".nav-links a").forEach(link => {
      link.addEventListener("click", () => {
        menuToggle.classList.remove("active");
        navLinks.classList.remove("active");
      });
    });
  });


  <script>
let editingTask = null;

function openModal() {
  document.getElementById("taskModal").classList.add("show");
}

function closeModal() {
  document.getElementById("taskModal").classList.remove("show");
  clearForm();
}

document.getElementById("openTaskModal").onclick = openModal;

function saveTask() {
  const title = document.getElementById("taskTitle").value;
  const desc = document.getElementById("taskDesc").value;
  const status = document.getElementById("taskStatus").value;

  if (!title) return alert("Enter task title");

  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <span class="tag ${status}">${status}</span>
    <h4>${title}</h4>
    <p>${desc}</p>
    <div class="actions">
      <button onclick="editTask(this)">Edit</button>
      <button onclick="deleteTask(this)">Delete</button>
    </div>
  `;

  document.querySelector(`.column:has(h3:contains("${status === 'todo' ? 'To Do' : status === 'progress' ? 'In Progress' : 'Completed'}"))`)
    ?.appendChild(card);

  closeModal();
}

function deleteTask(btn) {
  btn.closest('.card').remove();
}

function editTask(btn) {
  const card = btn.closest('.card');
  document.getElementById("taskTitle").value = card.querySelector("h4").innerText;
  document.getElementById("taskDesc").value = card.querySelector("p").innerText;
  openModal();
}
</script>
