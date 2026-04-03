const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('file-input');
const browseBtn = document.getElementById('browse-btn');
const uploadSection = document.querySelector('.upload-section');
const editorSection = document.getElementById('editor-section');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const loader = document.getElementById('loader');
const resetBtn = document.getElementById('reset-btn');
const downloadBtn = document.getElementById('download-btn');
const editModal = document.getElementById('edit-modal');
const editTextInput = document.getElementById('edit-text-input');
const fontStyleSelect = document.getElementById('font-style-select');
const cancelEditBtn = document.getElementById('cancel-edit-btn');
const saveEditBtn = document.getElementById('save-edit-btn');

let boxes = [];
let currentImage = new Image();
let originalImageFile = null;
let renderScale = 1;
let selectedBoxIndex = -1;
let currentOutputUrl = null;

const API_BASE = 'http://localhost:5000';

// Upload Handlers
browseBtn.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('click', () => fileInput.click());

dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

['dragleave', 'dragend'].forEach(type => {
    dropzone.addEventListener(type, () => {
        dropzone.classList.remove('dragover');
    });
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleFile(e.target.files[0]);
    }
});

async function handleFile(file) {
    if (!file.type.startsWith('image/')) {
        alert('Please upload an image file (PNG, JPG). Native PDF support is coming soon.');
        return;
    }

    originalImageFile = file;

    // Load image locally for canvas preview
    const reader = new FileReader();
    reader.onload = (e) => {
        currentImage.onload = () => {
            uploadSection.classList.add('hidden');
            editorSection.classList.remove('hidden');
            drawCanvas();
            uploadImageToBackend(file);
        };
        currentImage.src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function uploadImageToBackend(file) {
    loader.classList.remove('hidden');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Failed to OCR image');

        boxes = await response.json();
        drawCanvas();
    } catch (error) {
        console.error("Upload error:", error);
        alert("An error occurred during OCR text extraction.");
    } finally {
        loader.classList.add('hidden');
    }
}

function drawCanvas() {
    if (!currentImage.src) return;

    // Max display size
    const maxWidth = canvas.parentElement.clientWidth - 32;
    const maxHeight = window.innerHeight * 0.7;

    // Calculate scale to fit container while maintaining aspect ratio
    const scaleX = maxWidth / currentImage.naturalWidth;
    const scaleY = maxHeight / currentImage.naturalHeight;
    renderScale = Math.min(scaleX, scaleY, 1); // Never scale up beyond 1.0

    canvas.width = currentImage.naturalWidth * renderScale;
    canvas.height = currentImage.naturalHeight * renderScale;

    // Draw Image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);

    // Draw OCR Boxes
    boxes.forEach(box => {
        const scaledX = box.x * renderScale;
        const scaledY = box.y * renderScale;
        const scaledW = box.w * renderScale;
        const scaledH = box.h * renderScale;

        // Highlight text areas
        ctx.fillStyle = 'rgba(99, 102, 241, 0.2)'; // Primary color with opacity
        ctx.fillRect(scaledX, scaledY, scaledW, scaledH);
        
        ctx.strokeStyle = 'rgba(99, 102, 241, 0.8)';
        ctx.lineWidth = 1;
        ctx.strokeRect(scaledX, scaledY, scaledW, scaledH);
    });
}

// Window resize listener
window.addEventListener('resize', () => {
    if (!uploadSection.classList.contains('hidden')) return;
    drawCanvas();
});

// Canvas Click for Editing
canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    
    // Calculate click coordinates relative to canvas drawn size
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Map click back to unscaled image coordinates
    const unscaledX = clickX / renderScale;
    const unscaledY = clickY / renderScale;

    // Find clicked box
    selectedBoxIndex = boxes.findIndex(box => {
        return (unscaledX >= box.x && unscaledX <= box.x + box.w && 
                unscaledY >= box.y && unscaledY <= box.y + box.h);
    });

    if (selectedBoxIndex !== -1) {
        const selectedBox = boxes[selectedBoxIndex];
        editTextInput.value = selectedBox.text;
        editModal.classList.remove('hidden');
        editTextInput.focus();
    }
});

// Modal Actions
cancelEditBtn.addEventListener('click', () => {
    editModal.classList.add('hidden');
    selectedBoxIndex = -1;
});

saveEditBtn.addEventListener('click', async () => {
    if (selectedBoxIndex === -1) return;
    
    const newText = editTextInput.value.trim();
    if (!newText) return;
    
    const fontStyle = fontStyleSelect.value;

    const box = boxes[selectedBoxIndex];
    editModal.classList.add('hidden');
    loader.classList.remove('hidden');
    document.querySelector('.loader-overlay p').textContent = "Updating text...";

    try {
        const response = await fetch(`${API_BASE}/edit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                x: box.x,
                y: box.y,
                w: box.w,
                h: box.h,
                new_text: newText,
                font_style: fontStyle
            })
        });

        if (!response.ok) throw new Error('Edit failed');

        const result = await response.json();
        // The backend returns an 'output' which is the path, normally output.png
        // We'll need a way to fetch this updated image. For now, since it's local we
        // might need to create a route on the backend to serve this static file.
        // I will dynamically fetch it using a cache-busting query string
        
        // Let's replace the src with a fetch to get the actual image blob string to bypass cache
        const imgResponse = await fetch(`${API_BASE}/download?t=${new Date().getTime()}`);
        if(imgResponse.ok) {
            const blob = await imgResponse.blob();
            const url = URL.createObjectURL(blob);
            currentImage.src = url;
            currentOutputUrl = url;
            downloadBtn.disabled = false;
            
            // Re-upload to get updated OCR boxes? No, for now we will just hide the box
            // that was edited or we can keep the boxes and update the text property
            boxes[selectedBoxIndex].text = newText;
            
        } else {
             alert('Successfully edited, but failed to load the updated image preview.');
        }

    } catch (error) {
        console.error("Edit error:", error);
        alert("An error occurred while editing text.");
    } finally {
        loader.classList.add('hidden');
        document.querySelector('.loader-overlay p').textContent = "Processing text via OCR...";
    }
});

// Download button
downloadBtn.addEventListener('click', () => {
    if (!currentOutputUrl) return;
    const a = document.createElement('a');
    a.href = currentOutputUrl;
    a.download = 'edited_document.png';
    a.click();
});

// Reset Button
resetBtn.addEventListener('click', () => {
    uploadSection.classList.remove('hidden');
    editorSection.classList.add('hidden');
    boxes = [];
    currentImage = new Image();
    originalImageFile = null;
    currentOutputUrl = null;
    downloadBtn.disabled = true;
    fileInput.value = '';
});