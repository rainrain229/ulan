const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const sessionCodeInput = document.getElementById('sessionCode');
const statusEl = document.getElementById('status');

let stream = null;
let timer = null;
const clientId = `${Math.random().toString(36).slice(2)}-${Date.now()}`;

async function startCamera() {
  stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 }, audio: false });
  video.srcObject = stream;
  startBtn.disabled = true;
  stopBtn.disabled = false;
  statusEl.textContent = 'Camera started. Looking for a face...';
  startSending();
}

function stopCamera() {
  if (timer) { clearInterval(timer); timer = null; }
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
  startBtn.disabled = false;
  stopBtn.disabled = true;
  statusEl.textContent = 'Stopped';
}

function captureFrameBase64() {
  const w = video.videoWidth || 640;
  const h = video.videoHeight || 480;
  canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, w, h);
  return canvas.toDataURL('image/jpeg', 0.8);
}

function startSending() {
  timer = setInterval(async () => {
    try {
      const imageBase64 = captureFrameBase64();
      const sessionCode = sessionCodeInput.value.trim() || null;
      const res = await fetch('/api/recognize_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: clientId, session_code: sessionCode, image_base64: imageBase64 })
      });
      const data = await res.json();
      if (data.recognized) {
        const name = data.student ? data.student.full_name : 'Unknown';
        const live = data.liveness_ok ? 'live' : 'not live yet';
        statusEl.textContent = `Recognized ${name} (sim ${data.similarity?.toFixed(3)}) and ${live}`;
      } else {
        statusEl.textContent = data.message || 'No match yet...';
      }
    } catch (e) {
      console.error(e);
    }
  }, 600);
}

startBtn.addEventListener('click', startCamera);
stopBtn.addEventListener('click', stopCamera);