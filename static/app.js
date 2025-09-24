const $ = (s)=>document.querySelector(s);
const logs = $('#logs');

function write(t){ logs.textContent = t; }

// --- Slice-only button (still placeholder for now) ---
$('#sliceBtn')?.addEventListener('click', () => {
  write('Slice clicked (wire to /api/slice)…');
});

// --- Slice & Print button: send form data to Flask ---
$('#slicePrintBtn')?.addEventListener('click', async (e) => {
  e.preventDefault();

  const stl = $('#stl')?.files?.[0];
  const layer = $('#layer')?.value || '0.2';
  const infill = $('#infill')?.value || '15';

  if (!stl) {
    write('Please choose an STL file first.');
    return;
  }

  const fd = new FormData();
  fd.set('stlFile', stl);
  fd.set('layerHeight', layer);
  fd.set('infill', infill);

  write('⏳ Slicing and sending to printer…');

  try {
    const res = await fetch('/slice_and_print', { method:'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Slice & Print failed');

    write('✅ ' + (data.message || 'Slice & Print OK'));
  } catch (err) {
    write('❌ ' + err.message);
  }
});

$('#slicePrintBtn')?.addEventListener('click', async (e) => {
  e.preventDefault();

  const stl = $('#stl')?.files?.[0];
  const layer = $('#layer')?.value || '0.2';
  const infill = $('#infill')?.value || '15';
  if (!stl) { logs.textContent = 'Please choose an STL file.'; return; }

  const fd = new FormData();
  fd.set('stlFile', stl);
  fd.set('layerHeight', layer);
  fd.set('infill', infill);

  logs.textContent = '⏳ Slicing…';
  try {
    const res = await fetch('/slice_and_print', { method:'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Slice & Print failed');

    logs.textContent = '✅ ' + (data.message || 'Print started');
  } catch (err) {
    logs.textContent = '❌ ' + err.message;
  }
});

 // --- Pi Cam ---
const camImg = $('#camImg');

const CANDIDATES = [
  "http://192.168.0.11/webcam/?action=stream", // mjpg-streamer (Mainsail default)
  "http://192.168.0.11/webcam/stream.mjpg",    // alternative path
  "http://192.168.0.11:8080/?action=stream",   // ustreamer default port
  "http://192.168.0.11:8080/stream.mjpg"
];

async function pickCamera() {
  for (const url of CANDIDATES) {
    const ok = await testImage(url);
    if (ok) { camImg.src = url; return; }
  }
  // fallback: show message
  camImg.alt = "No camera stream found (configure streamer on the Pi)";
}

function testImage(url, timeout=2500) {
  return new Promise((resolve) => {
    const img = new Image();
    let done = false;
    const clean = (val)=>{ if (!done) { done = true; resolve(val); }};
    const t = setTimeout(()=> clean(false), timeout);
    img.onload = ()=> { clearTimeout(t); clean(true); };
    img.onerror = ()=> { clearTimeout(t); clean(false); };
    img.src = url + (url.includes('?') ? '&' : '?') + '_t=' + Date.now(); // cache-bust
  });
}

window.addEventListener('load', pickCamera);