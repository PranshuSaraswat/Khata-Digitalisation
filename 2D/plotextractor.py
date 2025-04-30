import cv2
import pytesseract
import re

# Configure tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load the layout image
image_path = r"C:\Users\Pranshu Saraswat\projects\Khata digitalization\2D\images\image.png"
img = cv2.imread(image_path)

# Resize (even bigger this time)
img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Apply Gaussian blur to reduce noise
gray = cv2.GaussianBlur(gray, (5,5), 0)

# Adaptive Thresholding (better for uneven lighting)
thresh = cv2.adaptiveThreshold(gray, 255, 
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                               cv2.THRESH_BINARY_INV, 
                               11, 2)

# OCR configuration (changed PSM mode to 11 = sparse text)
custom_config = r'--oem 3 --psm 11 -c tessedit_char_whitelist=0123456789'

# Run Tesseract OCR
detected_text = pytesseract.image_to_string(thresh, config=custom_config)

# Extract numbers
plot_numbers = re.findall(r'\d+', detected_text)

# Convert to integers
plot_numbers = [int(num) for num in plot_numbers]

# Print results
print("Detected Plot Numbers:", plot_numbers)
