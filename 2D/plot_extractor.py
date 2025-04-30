import cv2
import pytesseract
import re

# Configure tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Load the layout image
image_path = r"C:\Users\Pranshu Saraswat\projects\Khata digitalization\2D\images\image.png"
img = cv2.imread(image_path)

# Check if the image is loaded
if img is None:
    print("Error: Image not found at", image_path)
    exit()

# Resize with a smaller scaling factor
img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

# Display the full image in a resizable window
cv2.namedWindow("Full Image", cv2.WINDOW_NORMAL)
cv2.imshow("Full Image", img)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Convert to grayscale
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Display the grayscale image
cv2.imshow("Grayscale Image", gray)
cv2.waitKey(0)

# Apply Gaussian blur to reduce noise
gray = cv2.GaussianBlur(gray, (5, 5), 0)

# Adaptive Thresholding (better for uneven lighting)
thresh = cv2.adaptiveThreshold(gray, 255, 
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                               cv2.THRESH_BINARY_INV, 
                               11, 2)

# Display the thresholded image
cv2.imshow("Thresholded Image", thresh)
cv2.waitKey(0)

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

# Close all OpenCV windows
cv2.destroyAllWindows()
