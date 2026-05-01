# Khata Digitalization — How to run

Quick instructions to run the plot-analysis web tool included in this repo.

Prerequisites
- Python 3.8+ and `pip`
- (Optional) Node.js + `npm` if you want to install JS dependencies from `package.json`

Recommended Python setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install flask flask-cors opencv-python easyocr matplotlib numpy
# If EasyOCR requires torch on your platform, install torch separately per PyTorch instructions
```

Run the Flask server

```powershell
cd 2D
python app.py
```

Open in browser
- Main page: http://localhost:5000
- Plot analysis tool: http://localhost:5000/analysis

Notes
- The Flask entrypoint is `2D/app.py` which accepts image uploads at `/process-image`.
- The OCR and plot analysis logic lives in `2D/plotextractor.py` and outputs `plot_adjacency_data.json` and images saved to `extracted_plots/`.
- Static plot examples are in `2D/plot/` and images used for testing are in `2D/images/`.
- If you want to install Node dependencies (optional):

```powershell
# from repo root
npm install
```

If anything fails (especially EasyOCR/torch or OpenCV wheels on Windows), please tell me your Python version and OS so I can suggest exact install commands.

---
File: [README.md](README.md)
