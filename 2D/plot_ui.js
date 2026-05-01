let plotData = {};

const $ = (id) => document.getElementById(id);

function showElement(elementId) {
    $(elementId).classList.remove('hidden');
}

function hideElement(elementId) {
    $(elementId).classList.add('hidden');
}

function setPlotDetails(html) {
    $('plotDetails').innerHTML = html;
}

function displayError(message) {
    $('processingSection').innerHTML = `<div class="error">${message}</div>`;
}

async function uploadAndProcess(file) {
    showElement('processingSection');
    hideElement('searchSection');
    hideElement('svgSection');

    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch('/process-image', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Processing failed');
        }

        plotData = await response.json();
        hideElement('processingSection');
        showElement('searchSection');
        showElement('svgSection');

        await loadInteractiveSVG();
        showAllPlots();
        $('svgSection').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Error:', error);
        displayError('Error processing image. Please try again.');
    }
}

function searchPlot() {
    const plotNumber = $('plotSearch').value;
    const resultsDiv = $('results');

    if (!plotNumber) {
        resultsDiv.innerHTML = '<p>Please enter a plot number</p>';
        return;
    }

    const plot = plotData[plotNumber];
    if (!plot) {
        resultsDiv.innerHTML = '<p>Plot not found</p>';
        return;
    }

    displayPlots([plot]);
}

function showAllPlots() {
    displayPlots(Object.values(plotData));
}

function displayPlots(plots) {
    const resultsDiv = $('results');

    if (plots.length === 0) {
        resultsDiv.innerHTML = '<p>No plots found</p>';
        return;
    }

    let html = '';
    plots.forEach((plot) => {
        html += `
            <div class="plot-result">
                <div class="plot-number">Plot #${plot.plot_number}</div>
                <div class="adjacent-plots">
        `;

        if (!plot.adjacent || Object.keys(plot.adjacent).length === 0) {
            html += '<div class="direction-info">No adjacent plots</div>';
        } else {
            for (const [direction, plotNum] of Object.entries(plot.adjacent)) {
                const directionName = direction.charAt(0).toUpperCase() + direction.slice(1);
                html += `<div class="direction-info">${directionName}: ${plotNum}</div>`;
            }
        }

        html += `
                </div>
            </div>
        `;
    });

    resultsDiv.innerHTML = html;
}

function showPlotInfo(data) {
    let html = `<p><strong>Plot #${data.plot_number}</strong></p>`;

    if (data.dimensions) {
        html += `<p>North-South: ${data.dimensions.north_south}</p>`;
        html += `<p>East-West: ${data.dimensions.east_west}</p>`;
    }

    if (data.adjacent) {
        html += '<h5>Adjacent</h5>';
        for (const [direction, value] of Object.entries(data.adjacent)) {
            html += `<div>${direction}: ${value}</div>`;
        }
    }

    setPlotDetails(html);
}

function highlightRect(id) {
    const svg = document.querySelector('#svgContainer svg');
    if (!svg) {
        return;
    }

    svg.querySelectorAll('rect').forEach((rect) => {
        rect.setAttribute('stroke', '#00a000');
        rect.setAttribute('stroke-width', '2');
    });

    const selectedRect = svg.getElementById(id);
    if (selectedRect) {
        selectedRect.setAttribute('stroke', '#ff8800');
        selectedRect.setAttribute('stroke-width', '3');
    }
}

async function loadInteractiveSVG() {
    try {
        const response = await fetch('/extracted_plots/extracted_plots.svg');
        if (!response.ok) {
            return;
        }

        const svgText = await response.text();
        const container = $('svgContainer');
        container.innerHTML = svgText;

        if (container._plotClickHandler) {
            container.removeEventListener('click', container._plotClickHandler);
        }

        container._plotClickHandler = async (event) => {
            const rect = event.target.closest('rect');
            if (!rect) {
                return;
            }

            const match = (rect.id || '').match(/plot_(\d+)/);
            if (!match) {
                return;
            }

            const plotNumber = match[1];
            try {
                const jsonResponse = await fetch(`/plots/plot_${plotNumber}.json`);
                if (!jsonResponse.ok) {
                    throw new Error('No JSON');
                }

                const data = await jsonResponse.json();
                showPlotInfo(data);
                highlightRect(rect.id);
            } catch (error) {
                console.error(error);
                setPlotDetails('No data for this plot.');
            }
        };

        container.addEventListener('click', container._plotClickHandler);
    } catch (error) {
        console.error('SVG load error', error);
    }
}

function wireEvents() {
    $('fileInput').addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            $('uploadedImage').src = e.target.result;
            showElement('imageContainer');
        };
        reader.readAsDataURL(file);

        uploadAndProcess(file);
    });

    $('plotSearch').addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            searchPlot();
        }
    });
}

window.searchPlot = searchPlot;
window.showAllPlots = showAllPlots;
window.loadInteractiveSVG = loadInteractiveSVG;

window.addEventListener('DOMContentLoaded', wireEvents);
