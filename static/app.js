const $ = (s)=>document.querySelector(s);
const logs = $('#logs');

function write(msg) {
  logs.textContent = msg;
}

// --- Slice-only button (still placeholder) ---
$('#sliceBtn')?.addEventListener('click', () => {
  write('Slice clicked (download gcode) — feature placeholder');
});

// --- Slice & Print button ---
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

    write('✅ ' + (data.message || 'Print started'));
  } catch (err) {
    write('❌ ' + err.message);
  }
});