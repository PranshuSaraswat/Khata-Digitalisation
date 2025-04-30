import pytesseract
import cv2

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img = cv2.imread("layout.jpeg")

if img is None:
    print("❌ Image not found. Check the filename and path.")
    exit()

cv2.imshow("Loaded Image", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
