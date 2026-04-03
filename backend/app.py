from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pytesseract
import cv2
import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

app = Flask(__name__, static_folder='../frontend', static_url_path='/')
CORS(app)
pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    uploaded_path = "upload" + ext
    file.save(uploaded_path)
    
    filepath = "temp.png"
    
    if ext == '.pdf':
        doc = fitz.open(uploaded_path)
        page = doc.load_page(0)  # Load the first page
        pix = page.get_pixmap(dpi=300)
        pix.save(filepath)
        doc.close()
    else:
        import shutil
        shutil.copy(uploaded_path, filepath)

    img = cv2.imread(filepath)

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    
    results = []
    for i in range(len(data['text'])):
            if int(data['conf'][i]) > 60 and data['text'][i].strip() != "":
                results.append({
                     "text": data['text'][i],
                     "x": data['left'][i],
                     "y": data['top'][i],
                     "w": data['width'][i],
                     "h": data['height'][i]
                    })
    return jsonify(results)
@app.route('/edit', methods = ['POST'])
def edit():
    data=request.json
    x = data['x']
    y = data['y']
    w = data['w']
    h = data['h']
    new_text = data['new_text']
    font_name = data.get('font_style', 'sans-serif')

    img = cv2.imread("temp.png")

    # 1. Sample Background Color globally
    # A scanned document is mostly paper. The 95th percentile of the whole image is the pure paper color!
    # Downsample for lightning-fast percentile calculation
    small_img = cv2.resize(img, (200, int(200 * img.shape[0] / img.shape[1])))
    global_bg_color = np.percentile(small_img.reshape(-1, 3), 95, axis=0)
    bg_color = (int(global_bg_color[0]), int(global_bg_color[1]), int(global_bg_color[2]))

    # 2. Sample Text Color strictly from the darkest pixels of the local box
    box_roi = img[y:y+h, x:x+w]
    text_color = (0, 0, 0)
    if box_roi.size > 0:
        local_text = np.percentile(box_roi.reshape(-1, 3), 15, axis=0)
        text_color = (int(local_text[0]), int(local_text[1]), int(local_text[2]))

    # 3. Erase old text (draw over with calculated background color)
    # === 3 & 4: PILLOW SETUP ===
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)
    
    # Map UI font styles to system fonts using absolute Windows paths
    font_file = "C:\\Windows\\Fonts\\arial.ttf"
    if font_name == "serif": font_file = "C:\\Windows\\Fonts\\times.ttf"
    elif font_name == "monospace": font_file = "C:\\Windows\\Fonts\\cour.ttf"
    elif font_name == "bold": font_file = "C:\\Windows\\Fonts\\arialbd.ttf"
    
    try:
        font = ImageFont.truetype(font_file, int(h * 1.15))
    except IOError:
        font = ImageFont.load_default()

    # Calculate exact typographical advance width of new text
    if hasattr(draw, 'textlength'):
        new_w = int(draw.textlength(new_text, font=font))
    elif hasattr(font, 'getsize'):
        new_w = font.getsize(new_text)[0]
    else:
        new_w = w
        
    # PyTesseract bounding boxes are slightly generous. Also, newly calculated TTS typographical advance
    # often lacks scanned visual padding. Adding a 15% h buffer fixes text squishing against the next word.
    new_w += int(h * 0.2)

    rgb_bg_color = (bg_color[2], bg_color[1], bg_color[0])
    rgb_text_color = (text_color[2], text_color[1], text_color[0])

    # === 5: SMART TEXT REFLOW ===
    pad_top = int(h * 0.2)
    pad_bottom = int(h * 0.3)
    line_top = max(0, y - pad_top)
    line_bottom = min(img_pil.height, y + h + pad_bottom)
    
    block_left = x + w
    block_right = img_pil.width
    
    if block_left < block_right:
        # Copy the rest of the line
        rest_of_line = img_pil.crop((block_left, line_top, block_right, line_bottom))
        
        # Erase everything from x to the right edge with the background paper color
        draw.rectangle([x, line_top, block_right, line_bottom], fill=rgb_bg_color)
        
        # Paste the rest of the line at the new horizontally reflowed offset!
        new_block_left = x + new_w
        if new_block_left < img_pil.width:
            img_pil.paste(rest_of_line, (new_block_left, line_top))
    else:
        # If it's at the edge, just erase the word normally
        draw.rectangle([x, y, x+w, y+h], fill=rgb_bg_color)

    # Calculate baseline mathematically reliably
    # Given we use anchor="ls", we align the very bottom of non-descender letters to a baseline.
    # Often, OCR tightly bounds everything, so y+h is the bottom of the bounding box.
    # To prevent floating letters, placing the baseline at ~85% down the box is visually perfect.
    baseline_y = y + int(h * 0.85)

    # Draw the text at left-aligned `x` to seamlessly connect with the shifted block!
    draw.text((x, baseline_y), new_text, font=font, fill=rgb_text_color, anchor="ls")

    # Convert back to cv2 format for post-processing
    img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    # === 6: REALISM FILTERS (GRAIN & OPTICAL BLUR) ===
    # A true scan is never purely vector-crisp. By applying a slight Gaussian blur and CCD grain 
    # ONLY over the newly drawn text region, it perfectly vanishes into the visual noise of the document.
    degrade_top = max(0, int(y - h * 0.2))
    degrade_bottom = min(img.shape[0], int(y + h * 1.3))
    degrade_left = x
    degrade_right = min(img.shape[1], x + new_w)
    
    roi = img[degrade_top:degrade_bottom, degrade_left:degrade_right]
    if roi.size > 0:
        # 1. Scanner Optical Blur
        roi_blurred = cv2.GaussianBlur(roi, (3, 3), 0.3)
        
        # 2. Scanner Paper/Sensor Grain Noise
        noise = np.random.normal(0, 5, roi_blurred.shape).astype(np.float32)
        roi_distorted = np.clip(roi_blurred.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        
        img[degrade_top:degrade_bottom, degrade_left:degrade_right] = roi_distorted

    output_path = "output.png"
    cv2.imwrite(output_path, img)


    return jsonify({"output": output_path})

@app.route('/download', methods=['GET'])
def download():
    return send_file("output.png", mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
