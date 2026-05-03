import json
import os
import random
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import cv2
import easyocr
import matplotlib.pyplot as plt
import numpy as np

DEFAULT_IMAGE_PATH = r'C:\Users\Pranshu Saraswat\projects\Khata digitalization\2D\images\layout.jpeg'
OUTPUT_ROOT = 'extracted_plots'
PLOTS_DIR = os.path.join(OUTPUT_ROOT, 'plots')
RESULTS_DIR = os.path.join(OUTPUT_ROOT, 'results')
ANNOTATED_JSON_FILE = 'plot_adjacency_data.json'
SVG_FILE = os.path.join(OUTPUT_ROOT, 'extracted_plots.svg')
MEASUREMENT_PATTERN = re.compile(r'(?i)\b(\d{1,3})\s*ft\b')
PURE_NUMBER_PATTERN = re.compile(r'^\s*(\d{1,4})\s*$')


def ensure_output_dirs() -> None:
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    os.makedirs(PLOTS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)


def load_image(image_path: str) -> Optional[np.ndarray]:
    image = cv2.imread(image_path)
    if image is None:
        print(f'❌ Could not load image: {image_path}')
    return image


def preprocess_image(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        2,
    )


def find_contours(threshold_image: np.ndarray) -> List[np.ndarray]:
    contours, _ = cv2.findContours(threshold_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return contours


def initialize_reader() -> easyocr.Reader:
    print('📖 Initializing EasyOCR reader...')
    reader = easyocr.Reader(['en'], gpu=False)
    print('✅ EasyOCR reader ready!')
    return reader


def rotate_image(image: np.ndarray, rotation: str) -> np.ndarray:
    if rotation == 'cw':
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if rotation == 'ccw':
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().lower())


def extract_measurement_value(text: str) -> Optional[int]:
    normalized = normalize_text(text)
    match = MEASUREMENT_PATTERN.search(normalized)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def extract_pure_number(text: str) -> Optional[int]:
    normalized = normalize_text(text)
    match = PURE_NUMBER_PATTERN.match(normalized)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def is_top_region(bbox, image_height: int) -> bool:
    x_coords = [point[0] for point in bbox]
    y_coords = [point[1] for point in bbox]
    top_edge = min(y_coords)
    bottom_edge = max(y_coords)
    center_y = (top_edge + bottom_edge) / 2
    return center_y <= image_height * 0.35 or top_edge <= image_height * 0.22


def is_left_region(bbox, image_width: int) -> bool:
    x_coords = [point[0] for point in bbox]
    left_edge = min(x_coords)
    right_edge = max(x_coords)
    center_x = (left_edge + right_edge) / 2
    return center_x <= image_width * 0.35 or left_edge <= image_width * 0.22


def is_bottom_region(bbox, image_height: int) -> bool:
    y_coords = [point[1] for point in bbox]
    top_edge = min(y_coords)
    bottom_edge = max(y_coords)
    center_y = (top_edge + bottom_edge) / 2
    return center_y >= image_height * 0.65 or bottom_edge >= image_height * 0.78


def is_center_region(bbox, image_width: int, image_height: int) -> bool:
    x_coords = [point[0] for point in bbox]
    y_coords = [point[1] for point in bbox]
    center_x = (min(x_coords) + max(x_coords)) / 2
    center_y = (min(y_coords) + max(y_coords)) / 2
    return abs(center_x - image_width / 2) <= image_width * 0.28 and abs(center_y - image_height / 2) <= image_height * 0.28


def collect_ocr_results(image: np.ndarray, reader: easyocr.Reader, rotation: str = 'none'):
    ocr_input = rotate_image(image, rotation)
    try:
        results = reader.readtext(
            ocr_input,
            text_threshold=0.4,
            low_text=0.2,
            width_ths=0.4,
            height_ths=0.4,
            mag_ratio=1.5,
            slope_ths=0.3,
            ycenter_ths=0.7,
            add_margin=0.1,
        )
    except Exception as exc:
        print(f'OCR Error: {str(exc)}')
        return []

    return [
        {
            'rotation': rotation,
            'bbox': bbox,
            'text': text,
            'confidence': confidence,
        }
        for bbox, text, confidence in results
    ]


def extract_plot_metadata(plot_image: np.ndarray, reader: easyocr.Reader) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    height, width = plot_image.shape[:2]
    original_results = collect_ocr_results(plot_image, reader, rotation='none')
    rotated_cw_results = collect_ocr_results(plot_image, reader, rotation='cw')
    rotated_ccw_results = collect_ocr_results(plot_image, reader, rotation='ccw')

    plot_number_candidates = []
    north_south_candidates = []
    east_west_candidates = []

    for candidate in original_results:
        text = candidate['text']
        bbox = candidate['bbox']
        confidence = candidate['confidence']

        measurement_value = extract_measurement_value(text)
        if measurement_value is not None:
            if is_top_region(bbox, height):
                north_south_candidates.append((measurement_value, confidence))
            continue

        pure_number = extract_pure_number(text)
        if pure_number is not None:
            if is_center_region(bbox, width, height):
                plot_number_candidates.append((pure_number, confidence))

    for candidate in rotated_ccw_results:
        text = candidate['text']
        bbox = candidate['bbox']
        confidence = candidate['confidence']

        measurement_value = extract_measurement_value(text)
        if measurement_value is None:
            continue

        if is_bottom_region(bbox, width):
            east_west_candidates.append((measurement_value, confidence))

    for candidate in rotated_cw_results:
        text = candidate['text']
        bbox = candidate['bbox']
        confidence = candidate['confidence']

        measurement_value = extract_measurement_value(text)
        if measurement_value is None:
            continue

        if is_top_region(bbox, width):
            east_west_candidates.append((measurement_value, confidence))

    def pick_best(candidates):
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[1], reverse=True)
        return candidates[0][0]

    plot_number = pick_best(plot_number_candidates)
    north_south = pick_best(north_south_candidates)
    east_west = pick_best(east_west_candidates)

    return plot_number, north_south, east_west


def extract_number_from_plot(plot_image, reader):
    """Extract number from a single plot using EasyOCR."""
    plot_number, _, _ = extract_plot_metadata(plot_image, reader)
    return plot_number


def extract_plot_candidates(
    image: np.ndarray,
    contours: List[np.ndarray],
    reader: easyocr.Reader,
) -> Tuple[List[Dict[str, int]], int]:
    min_area = 200
    max_area = 40000
    plot_info: List[Dict[str, int]] = []
    failed_ocr_count = 0

    print('\n🔍 Processing detected plots...')

    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if not (min_area < area < max_area):
            continue

        x, y, w, h = cv2.boundingRect(cnt)
        plot_img = image[y:y + h, x:x + w]

        print(f'📝 Processing plot {i + 1} at position ({x}, {y})...')
        detected_number, north_south, east_west = extract_plot_metadata(plot_img, reader)
        if detected_number is None:
            print(f'❌ Failed to detect number for plot at ({x}, {y})')
            failed_ocr_count += 1
            continue

        print(f'✅ Detected number: {detected_number}')
        if north_south is not None:
            print(f'   ↳ North-South: {north_south}')
        if east_west is not None:
            print(f'   ↳ East-West: {east_west}')

        plot_info.append(
            {
                'number': detected_number,
                'north_south': north_south,
                'east_west': east_west,
                'x': x,
                'y': y,
                'w': w,
                'h': h,
            }
        )

    return plot_info, failed_ocr_count


def are_adjacent(plot1, plot2, tolerance=15):
    x1, y1, w1, h1 = plot1['x'], plot1['y'], plot1['w'], plot1['h']
    x2, y2, w2, h2 = plot2['x'], plot2['y'], plot2['w'], plot2['h']

    left1, right1, top1, bottom1 = x1, x1 + w1, y1, y1 + h1
    left2, right2, top2, bottom2 = x2, x2 + w2, y2, y2 + h2

    horizontal_adjacent = False
    if abs(right1 - left2) <= tolerance or abs(right2 - left1) <= tolerance:
        vertical_overlap = min(bottom1, bottom2) - max(top1, top2)
        min_height = min(h1, h2)
        if vertical_overlap > min_height * 0.3:
            horizontal_adjacent = True

    vertical_adjacent = False
    if abs(bottom1 - top2) <= tolerance or abs(bottom2 - top1) <= tolerance:
        horizontal_overlap = min(right1, right2) - max(left1, left2)
        min_width = min(w1, w2)
        if horizontal_overlap > min_width * 0.3:
            vertical_adjacent = True

    return horizontal_adjacent or vertical_adjacent


def get_direction(plot1, plot2):
    x1, y1, w1, h1 = plot1['x'], plot1['y'], plot1['w'], plot1['h']
    x2, y2, w2, h2 = plot2['x'], plot2['y'], plot2['w'], plot2['h']

    cx1, cy1 = x1 + w1 // 2, y1 + h1 // 2
    cx2, cy2 = x2 + w2 // 2, y2 + h2 // 2

    if abs(cx1 - cx2) > abs(cy1 - cy2):
        return 'east' if cx2 > cx1 else 'west'
    return 'south' if cy2 > cy1 else 'north'


def build_plot_data(plot_info: List[Dict[str, int]]) -> Dict[int, Dict[str, object]]:
    print('\n🔗 Analyzing adjacency relationships...')
    plot_data: Dict[int, Dict[str, object]] = {}

    for i, plot1 in enumerate(plot_info):
        plot_number = plot1['number']
        adjacent_plots = {'north': 'Road', 'south': 'Road', 'east': 'Road', 'west': 'Road'}

        for j, plot2 in enumerate(plot_info):
            if i == j:
                continue
            if are_adjacent(plot1, plot2, tolerance=15):
                direction = get_direction(plot1, plot2)
                adjacent_plots[direction] = plot2['number']

        plot_data[plot_number] = {
            'plot_number': plot_number,
            'adjacent': adjacent_plots,
            'dimension': {
                'north-south': plot1.get('north_south'),
                'east-west': plot1.get('east_west'),
            },
        }
        adjacent_str = ', '.join([f'{direction}: {value}' for direction, value in adjacent_plots.items()])
        print(f'Plot {plot_number} -> {adjacent_str}')

    return plot_data


def build_annotated_image(image: np.ndarray, plot_info: List[Dict[str, int]]) -> np.ndarray:
    annotated = image.copy()
    for plot in plot_info:
        x, y, w, h = plot['x'], plot['y'], plot['w'], plot['h']
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(annotated, str(plot['number']), (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
    return annotated


def display_annotated_image(image: np.ndarray, plot_info: List[Dict[str, int]]) -> None:
    try:
        annotated = build_annotated_image(image, plot_info)
        plt.figure(figsize=(12, 8))
        plt.title(f'Plot Detection with OCR Numbers: {len(plot_info)} plots identified')
        plt.imshow(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB))
        plt.axis('off')
        plt.show()
    except Exception:
        pass


def save_plot_adjacency_json(plot_data: Dict[int, Dict[str, object]]) -> str:
    ensure_output_dirs()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_filename = f'plot_adjacency_{timestamp}.json'
    json_filepath = os.path.join(RESULTS_DIR, json_filename)
    
    with open(json_filepath, 'w', encoding='utf-8') as file_handle:
        json.dump(plot_data, file_handle, indent=2)
    print(f'\n💾 JSON data saved to: {json_filepath}')
    
    # Also save to root for backward compatibility
    with open(ANNOTATED_JSON_FILE, 'w', encoding='utf-8') as file_handle:
        json.dump(plot_data, file_handle, indent=2)
    
    return timestamp


def save_per_plot_json(plot_info: List[Dict[str, int]], plot_data: Dict[int, Dict[str, object]]) -> None:
    ensure_output_dirs()
    for plot in plot_info:
        num = plot['number']
        per_plot = {
            'plot_number': num,
            'adjacent': plot_data.get(num, {}).get('adjacent', {}),
            'dimension': {
                'north-south': plot.get('north_south'),
                'east-west': plot.get('east_west'),
            },
        }
        with open(os.path.join(PLOTS_DIR, f'plot_{num}.json'), 'w', encoding='utf-8') as file_handle:
            json.dump(per_plot, file_handle, indent=2)


def save_plot_image(plot: Dict[str, int], image: np.ndarray) -> None:
    x, y, w, h = plot['x'], plot['y'], plot['w'], plot['h']
    plot_img = image[y:y + h, x:x + w]
    cv2.imwrite(os.path.join(OUTPUT_ROOT, f'plot_{plot["number"]}.png'), plot_img)


def export_interactive_svg(image: np.ndarray, plot_info: List[Dict[str, int]], timestamp: str = '') -> None:
    height, width = image.shape[0], image.shape[1]
    svg_lines: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<style>',
        '  .plot-area { fill: rgba(0,0,0,0); stroke: #00a000; stroke-width: 2; cursor: pointer; transition: all 0.18s ease; }',
        '  .plot-area:hover { fill: rgba(37, 99, 235, 0.12); stroke: #2563eb; stroke-width: 3.5; filter: drop-shadow(0 0 4px rgba(37, 99, 235, 0.35)); }',
        '  .plot-area.selected { fill: rgba(245, 158, 11, 0.14); stroke: #f59e0b; stroke-width: 4; }',
        '  .plot-label { pointer-events: none; user-select: none; font-family: Arial, sans-serif; font-weight: 600; }',
        '</style>',
    ]

    for plot in plot_info:
        num = plot['number']
        x, y, w, h = plot['x'], plot['y'], plot['w'], plot['h']
        svg_lines.append(
            f'<rect id="plot_{num}" class="plot-area" x="{x}" y="{y}" width="{w}" height="{h}" />'
        )
        text_x = x + 4
        text_y = y + min(24, h - 4)
        svg_lines.append(
            f'<text class="plot-label" x="{text_x}" y="{text_y}" font-size="16" fill="#0055aa">{num}</text>'
        )

    svg_lines.append('</svg>')
    ensure_output_dirs()
    
    # Save timestamped version
    if timestamp:
        svg_filename = f'extracted_plots_{timestamp}.svg'
        svg_filepath = os.path.join(RESULTS_DIR, svg_filename)
        with open(svg_filepath, 'w', encoding='utf-8') as file_handle:
            file_handle.write('\n'.join(svg_lines))
        print(f'💾 SVG saved to: {svg_filepath}')
    
    # Save current version for backward compatibility
    with open(SVG_FILE, 'w', encoding='utf-8') as file_handle:
        file_handle.write('\n'.join(svg_lines))
    print(f'💾 SVG saved to: {SVG_FILE}')


def analyze_plots_with_ocr(image_path: str = DEFAULT_IMAGE_PATH):
    print('🚀 Starting Combined Plot Detection and OCR Analysis...')
    print('=' * 60)

    image = load_image(image_path)
    if image is None:
        return {}

    threshold_image = preprocess_image(image)
    contours = find_contours(threshold_image)
    reader = initialize_reader()

    ensure_output_dirs()
    plot_info, failed_ocr_count = extract_plot_candidates(image, contours, reader)

    print('\n📊 Plot Detection Summary:')
    print(f'✅ Successfully processed: {len(plot_info)} plots')
    print(f'❌ Failed OCR: {failed_ocr_count} plots')

    plot_data = build_plot_data(plot_info)
    timestamp = save_plot_adjacency_json(plot_data)
    export_interactive_svg(image, plot_info, timestamp)
    display_annotated_image(image, plot_info)

    print('\n📋 JSON OUTPUT:')
    print('=' * 60)
    print(json.dumps(plot_data, indent=2))

    return plot_data


def main():
    plot_data = analyze_plots_with_ocr()

    print('\n🎉 Analysis complete!')
    print(f'📈 Total plots analyzed: {len(plot_data)}')

    if plot_data:
        print('\n📝 Example - First plot data:')
        first_plot = next(iter(plot_data.values()))
        print(f"Plot {first_plot['plot_number']}:")
        print(f"  Adjacent plots: {first_plot['adjacent']}")


if __name__ == '__main__':
    main()
