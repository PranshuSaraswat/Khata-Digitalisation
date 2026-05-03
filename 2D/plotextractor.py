import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import re
import easyocr
import json
import random

from typing import List, Dict
from plot_core import analyze_plots_with_ocr, main


if __name__ == '__main__':
    main()

def extract_number_from_plot(plot_image, reader):
    """
    Extract number from a single plot using EasyOCR
    """
    try:
        # Use EasyOCR with tuned parameters
        ocr_results = reader.readtext(
            plot_image,
            text_threshold=0.4,
            low_text=0.2,
            width_ths=0.4,
            height_ths=0.4,
            mag_ratio=1.5,
            slope_ths=0.3,
            ycenter_ths=0.7,
            add_margin=0.1
        )

        # Process detected text
        number_candidates = []

        for bbox, text, confidence in ocr_results:
            # Extract numbers from text
            numbers = re.findall(r'\d+', text)

            for num_str in numbers:
                try:
                    number = int(num_str)
                    adjusted_confidence = confidence

                    # Bonus for 2-digit numbers in expected range
                    if len(num_str) == 2 and 10 <= number <= 90:
                        adjusted_confidence += 0.1
                    # Bonus for single digits
                    elif len(num_str) == 1 and 1 <= number <= 9:
                        adjusted_confidence += 0.2

                    number_candidates.append({
                        'number': number,
                        'confidence': min(adjusted_confidence, 1.0),
                        'digit_count': len(num_str)
                    })
                except ValueError:
                    continue

        # Select best candidate (prefer 2-digit numbers)
        if number_candidates:
            number_candidates.sort(key=lambda x: (x['digit_count'] == 2, x['confidence']), reverse=True)
            return number_candidates[0]['number']

        return None

    except Exception as e:
        print(f"OCR Error: {str(e)}")
        return None

def are_adjacent(plot1, plot2, tolerance=15):
    """
    Check if two plots are actually adjacent (sharing edges directly, not diagonally)
    """
    x1, y1, w1, h1 = plot1['x'], plot1['y'], plot1['w'], plot1['h']
    x2, y2, w2, h2 = plot2['x'], plot2['y'], plot2['w'], plot2['h']

    # Calculate boundaries
    left1, right1, top1, bottom1 = x1, x1 + w1, y1, y1 + h1
    left2, right2, top2, bottom2 = x2, x2 + w2, y2, y2 + h2

    # Check horizontal adjacency (plots side by side)
    horizontal_adjacent = False
    if abs(right1 - left2) <= tolerance or abs(right2 - left1) <= tolerance:
        vertical_overlap = min(bottom1, bottom2) - max(top1, top2)
        min_height = min(h1, h2)
        if vertical_overlap > min_height * 0.3:  # At least 30% overlap
            horizontal_adjacent = True

    # Check vertical adjacency (plots above/below each other)
    vertical_adjacent = False
    if abs(bottom1 - top2) <= tolerance or abs(bottom2 - top1) <= tolerance:
        horizontal_overlap = min(right1, right2) - max(left1, left2)
        min_width = min(w1, w2)
        if horizontal_overlap > min_width * 0.3:  # At least 30% overlap
            vertical_adjacent = True

    return horizontal_adjacent or vertical_adjacent

def get_direction(plot1, plot2):
    """
    Get direction from plot1 to plot2 for adjacent plots
    """
    x1, y1, w1, h1 = plot1['x'], plot1['y'], plot1['w'], plot1['h']
    x2, y2, w2, h2 = plot2['x'], plot2['y'], plot2['w'], plot2['h']

    # Calculate centers
    cx1, cy1 = x1 + w1//2, y1 + h1//2
    cx2, cy2 = x2 + w2//2, y2 + h2//2

    # Determine direction based on relative position
    if abs(cx1 - cx2) > abs(cy1 - cy2):
        # Horizontal relationship is stronger
        if cx2 > cx1:
            return 'east'
        else:
            return 'west'
    else:
        # Vertical relationship is stronger
        if cy2 > cy1:
            return 'south'
        else:
            return 'north'

def analyze_plots_with_ocr(image_path=r'C:\Users\Pranshu Saraswat\projects\Khata digitalization\2D\images\layout.jpeg'):
    """
    Main function to detect plots, extract numbers using OCR, and analyze adjacency
    If no plot is adjacent in a direction, assign "Road"
    """

    print("🚀 Starting Combined Plot Detection and OCR Analysis...")
    print("=" * 60)

    # Read and process image
    img = cv2.imread(image_path)
    if img is None:
        print(f"❌ Could not load image: {image_path}")
        return {}

    img_all_plots = img.copy()

    # Preprocessing for contour detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)

    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Initialize EasyOCR
    print("📖 Initializing EasyOCR reader...")
    reader = easyocr.Reader(['en'], gpu=False)
    print("✅ EasyOCR reader ready!")

    # Filter contours and extract plot information
    min_area = 200
    max_area = 40000
    plot_info = []
    failed_ocr_count = 0

    # Output folder
    output_dir = "extracted_plots"
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n🔍 Processing detected plots...")

    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if min_area < area < max_area:
            x, y, w, h = cv2.boundingRect(cnt)

            # Extract plot image
            plot_img = img[y:y+h, x:x+w]

            # Use OCR to get the actual number
            print(f"📝 Processing plot {i+1} at position ({x}, {y})...")
            detected_number = extract_number_from_plot(plot_img, reader)

            if detected_number is not None:
                print(f"✅ Detected number: {detected_number}")

                # Draw rectangle and number on main image
                cv2.rectangle(img_all_plots, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(img_all_plots, str(detected_number), (x + 5, y + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)

                # Save plot image with detected number as filename
                cv2.imwrite(f"{output_dir}/plot_{detected_number}.png", plot_img)

                # Store plot information
                plot_info.append({
                    'number': detected_number,
                    'x': x, 'y': y, 'w': w, 'h': h
                })
            else:
                print(f"❌ Failed to detect number for plot at ({x}, {y})")
                failed_ocr_count += 1

                # Still draw rectangle but mark as unidentified
                cv2.rectangle(img_all_plots, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(img_all_plots, "?", (x + 5, y + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    print(f"\n📊 Plot Detection Summary:")
    print(f"✅ Successfully processed: {len(plot_info)} plots")
    print(f"❌ Failed OCR: {failed_ocr_count} plots")

    # Analyze adjacency relationships - assign "Road" if no adjacent plot
    print(f"\n🔗 Analyzing adjacency relationships...")
    plot_data = {}

    for i, plot1 in enumerate(plot_info):
        plot_number = plot1['number']
        
        # Initialize all directions as "Road"
        adjacent_plots = {
            'north': 'Road',
            'south': 'Road', 
            'east': 'Road',
            'west': 'Road'
        }

        # Check for adjacent plots and override "Road" if plot found
        for j, plot2 in enumerate(plot_info):
            if i == j:
                continue

            # Check if plots are adjacent
            if are_adjacent(plot1, plot2, tolerance=15):
                direction = get_direction(plot1, plot2)
                adjacent_plots[direction] = plot2['number']

        # Store in JSON format
        plot_data[plot_number] = {
            "plot_number": plot_number,
            "adjacent": adjacent_plots
        }

        # Print adjacency info
        adjacent_str = ", ".join([f"{direction}: {value}" for direction, value in adjacent_plots.items()])
        print(f"Plot {plot_number} -> {adjacent_str}")

    # Display the annotated image (optional)
    try:
        plt.figure(figsize=(12, 8))
        plt.title(f"Plot Detection with OCR Numbers: {len(plot_info)} plots identified")
        plt.imshow(cv2.cvtColor(img_all_plots, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        plt.show()
    except Exception:
        # Matplotlib display may fail in headless environments; ignore
        pass

    # Save JSON output
    output_file = "plot_adjacency_data.json"
    with open(output_file, 'w') as f:
        json.dump(plot_data, f, indent=2)

    print(f"\n💾 JSON data saved to: {output_file}")

    # Prepare output folders for interactive UI
    output_dir = "extracted_plots"
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)

    # Write per-plot JSON files (with placeholder/random dimensions)
    for p in plot_info:
        num = p['number']
        per_plot = {
            'plot_number': num,
            'adjacent': plot_data.get(num, {}).get('adjacent', {}),
            'dimensions': {
                'north_south': random.randint(30, 60),
                'east_west': random.randint(10, 40)
            }
        }
        with open(os.path.join(plots_dir, f'plot_{num}.json'), 'w') as pf:
            json.dump(per_plot, pf, indent=2)

    # Create a simple SVG that mirrors detected plot rectangles so front-end can interact
    height, width = img.shape[0], img.shape[1]
    svg_lines: List[str] = []
    svg_lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')

    # Add translucent background image as data URL (optional) - omitted to keep SVG small
    for p in plot_info:
        num = p['number']
        x, y, w, h = p['x'], p['y'], p['w'], p['h']
        rect = (f'<rect id="plot_{num}" x="{x}" y="{y}" width="{w}" height="{h}" '
                f'style="fill:rgba(0,0,0,0);stroke:#00a000;stroke-width:2;cursor:pointer;" />')
        text_x = x + 4
        text_y = y + min(24, h - 4)
        label = (f'<text x="{text_x}" y="{text_y}" font-size="16" fill="#0055aa">{num}</text>')
        svg_lines.append(rect)
        svg_lines.append(label)

    svg_lines.append('</svg>')
    svg_content = "\n".join(svg_lines)
    svg_path = os.path.join(output_dir, 'extracted_plots.svg')
    with open(svg_path, 'w', encoding='utf-8') as svf:
        svf.write(svg_content)

    print(f"💾 SVG saved to: {svg_path}")

    print(f"\n📋 JSON OUTPUT:")
    print("=" * 60)
    print(json.dumps(plot_data, indent=2))

    return plot_data

# MAIN EXECUTION
# ==============

# Run the combined analysis
#plot_data = analyze_plots_with_ocr()

#print(f"\n🎉 Analysis complete!")
#print(f"📈 Total plots analyzed: {len(plot_data)}")

# Example of accessing the data
#if plot_data:
    print(f"\n📝 Example - First plot data:")
    first_plot = next(iter(plot_data.values()))
    print(f"Plot {first_plot['plot_number']}:")
    print(f"  Adjacent plots: {first_plot['adjacent']}")

    # MAIN EXECUTION
# ==============

def main():
    
    # Run the combined analysis
    plot_data = analyze_plots_with_ocr()

    print(f"\n🎉 Analysis complete!")
    print(f"📈 Total plots analyzed: {len(plot_data)}")

    # Example of accessing the data
    if plot_data:
        print(f"\n📝 Example - First plot data:")
        first_plot = next(iter(plot_data.values()))
        print(f"Plot {first_plot['plot_number']}:")
        print(f"  Adjacent plots: {first_plot['adjacent']}")

# Only run main() when script is executed directly, not when imported
if __name__ == "__main__":
    main()


# Re-export the modular implementation so imports use the new core module.
from plot_core import analyze_plots_with_ocr as analyze_plots_with_ocr  # noqa: E402,F401
from plot_core import main as main  # noqa: E402,F401