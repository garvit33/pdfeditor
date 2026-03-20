from flask import Flask, request, jsonify
import pytesseract
import cv2
from PIL import Image

app = Flask(__name__)
pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    filepath = "temp.png"
    file.save(filepath)

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

                img = cv2.imread("temp.png")

                cv2.rectangle(img, (x, y), (x+w, y+h),(245,245,245),-1)

                font_scale = h/42
                y_text = y + int(h * 0.8)
                cv2.putText(
                     img,
                     new_text,
                     (x,y_text),
                     cv2.FONT_HERSHEY_COMPLEX,
                     font_scale,
                     (0,0,0),
                     1
                )
        
                output_path = "output.png"
                cv2.imwrite(output_path,img)


                return jsonify({"output": output_path})
if __name__ == '__main__':
    app.run(debug=True)
