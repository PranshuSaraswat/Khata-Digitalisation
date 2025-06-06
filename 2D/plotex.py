import cv2
import pytesseract

# Configure tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load the image
image_path = r"C:\Users\Pranshu Saraswat\projects\Khata digitalization\2D\images\image.png"
image = cv2.imread(image_path)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

# Find contours
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

plot_numbers = []
for cnt in contours:
    x, y, w, h = cv2.boundingRect(cnt)
    if 30 < w < 200 and 30 < h < 200:  # Heuristic filters for plot size
        plot = image[y:y+h, x:x+w]
        text = pytesseract.image_to_string(plot, config='--psm 6')
        if text.strip().isdigit():
            plot_numbers.append(text.strip())

print("Detected plot numbers:", plot_numbers)
