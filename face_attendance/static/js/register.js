const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const startBtn = document.getElementById('startBtn');
const captureBtn = document.getElementById('captureBtn');
const submitBtn = document.getElementById('submitBtn');
const thumbs = document.getElementById('thumbs');
const statusEl = document.getElementById('status');

const studentCode = document.getElementById('studentCode');
const fullName = document.getElementById('fullName');
const className = document.getElementById('className');

let stream = null;
let images = [];

async function startCamera() {
  stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
  video.srcObject = stream;
  startBtn.disabled = true;
  captureBtn.disabled = false;
}

function capture() {
  const w = video.videoWidth || 640;
  const h = video.videoHeight || 480;
  canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, w, h);
  canvas.toBlob(blob => {
    images.push(blob);
    const url = URL.createObjectURL(blob);
    const img = document.createElement('img');
    img.src = url;
    thumbs.appendChild(img);
    submitBtn.disabled = images.length < 3;
  }, 'image/jpeg', 0.9);
}

async function submit() {
  if (!studentCode.value || !fullName.value) {
    statusEl.textContent = 'Please enter student code and full name';
    return;
  }
  const form = new FormData();
  form.append('student_code', studentCode.value.trim());
  form.append('full_name', fullName.value.trim());
  if (className.value.trim()) form.append('class_name', className.value.trim());
  images.forEach((blob, idx) => form.append('files', blob, `img_${idx}.jpg`));

  const res = await fetch('/api/register_student', { method: 'POST', body: form });
  if (res.ok) {
    statusEl.textContent = 'Registered successfully';
    images = [];
    thumbs.innerHTML = '';
  } else {
    const data = await res.json().catch(() => ({ detail: 'Error' }));
    statusEl.textContent = data.detail || 'Registration failed';
  }
}

startBtn.addEventListener('click', startCamera);
captureBtn.addEventListener('click', capture);
submitBtn.addEventListener('click', submit);