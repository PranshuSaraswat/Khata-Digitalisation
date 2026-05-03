let plotData = {};

const $ = (id) => document.getElementById(id);

function getElement(elementId) {
    return $(elementId);
}

function hasElement(elementId) {
    return Boolean($(elementId));
}

function showElement(elementId) {
    const element = getElement(elementId);
    if (element) {
        element.classList.remove('hidden');
    }
}

function hideElement(elementId) {
    const element = getElement(elementId);
    if (element) {
        element.classList.add('hidden');
    }
}

function setPlotDetails(html) {
    const details = getElement('plotDetails');
    if (details) {
        details.innerHTML = html;
    }
}

function displayError(message) {
    const processingSection = getElement('processingSection');
    if (processingSection) {
        processingSection.innerHTML = `<div class="error">${message}</div>`;
    }
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
        showElement('openSvgButton');

        await loadInteractiveSVG();
        showAllPlots();
        const svgSection = getElement('svgSection');
        if (svgSection) {
            svgSection.scrollIntoView({ behavior: 'smooth' });
        }
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

async function loadSavedResults() {
    try {
        const response = await fetch('/api/saved-results');
        if (!response.ok) {
            return;
        }
        
        const results = await response.json();
        if (results.length === 0) {
            return;
        }
        
        displaySavedResults(results);
    } catch (error) {
        console.error('Error loading saved results:', error);
    }
}

function displaySavedResults(results) {
    const resultsDiv = $('results');
    
    let html = '<h4>📁 Previously Analyzed Results</h4>';
    html += '<div class="saved-results-list">';
    
    results.forEach((result) => {
        const date = new Date(result.timestamp.replace(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/, '$1-$2-$3T$4:$5:$6'));
        const dateStr = date.toLocaleString();
        
        html += `
            <div class="saved-result-item">
                <div class="result-date">${dateStr}</div>
                <button onclick="loadSavedResult('${result.json_url}', '${result.svg_url}')" class="load-result-btn">Load Result</button>
            </div>
        `;
    });
    
    html += '</div>';
    resultsDiv.innerHTML = html;
}

async function loadSavedResult(jsonUrl, svgUrl) {
    try {
        const response = await fetch(jsonUrl);
        if (!response.ok) {
            throw new Error('Failed to load result');
        }
        
        plotData = await response.json();
        showElement('searchSection');
        showElement('svgSection');
        showElement('openSvgButton');
        
        // Update SVG URL for the embedded viewer
        const container = $('svgContainer');
        if (container) {
            const svgResponse = await fetch(svgUrl);
            if (svgResponse.ok) {
                const svgText = await svgResponse.text();
                container.innerHTML = svgText;
                attachSVGClickHandler();
            }
        }
        
        showAllPlots();
        const svgSection = getElement('svgSection');
        if (svgSection) {
            svgSection.scrollIntoView({ behavior: 'smooth' });
        }
    } catch (error) {
        console.error('Error loading result:', error);
        displayError('Error loading result. Please try again.');
    }
}

function attachSVGClickHandler() {
    const container = $('svgContainer');
    if (!container) {
        return;
    }
    
    if (container._plotClickHandler) {
        container.removeEventListener('click', container._plotClickHandler);
    }

    container._plotClickHandler = (event) => {
        const rect = event.target.closest('rect');
        if (!rect) {
            return;
        }

        const match = (rect.id || '').match(/plot_(\d+)/);
        if (!match) {
            return;
        }

        const plotNumber = match[1];
        const data = plotData[plotNumber];
        if (data) {
            showPlotInfo(data);
            highlightRect(rect.id);
        } else {
            setPlotDetails('No data for this plot.');
        }
    };

    container.addEventListener('click', container._plotClickHandler);
}

async function populateResultsDropdown() {
    const dropdown = $('resultsDropdown');
    if (!dropdown) {
        return;
    }

    try {
        const response = await fetch('/api/saved-results');
        if (!response.ok) {
            dropdown.innerHTML = '<option value="">Failed to load results</option>';
            return;
        }
        
        const results = await response.json();
        
        dropdown.innerHTML = '<option value="">-- Select a Result --</option>';

        if (!Array.isArray(results) || results.length === 0) {
            dropdown.innerHTML = '<option value="">No saved results found</option>';
            const container = $('svgContainer');
            if (container) {
                container.innerHTML = '<div class="hint">No saved SVG results found yet. Process an image first.</div>';
            }
            return;
        }

        results.forEach((result) => {
            const date = new Date(result.timestamp.replace(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/, '$1-$2-$3T$4:$5:$6'));
            const dateStr = date.toLocaleString();
            const option = document.createElement('option');
            option.value = JSON.stringify({ json: result.json_url, svg: result.svg_url });
            option.textContent = dateStr;
            dropdown.appendChild(option);
        });
        
        // Set the latest result as default
        if (results.length > 0) {
            dropdown.value = JSON.stringify({ json: results[0].json_url, svg: results[0].svg_url });
            await loadSelectedResult();
        }
    } catch (error) {
        console.error('Error loading results dropdown:', error);
        dropdown.innerHTML = '<option value="">Error loading results</option>';
    }
}

async function loadSelectedResult() {
    const dropdown = $('resultsDropdown');
    if (!dropdown || !dropdown.value) {
        return;
    }
    
    try {
        const urls = JSON.parse(dropdown.value);
        const jsonResponse = await fetch(urls.json);
        if (!jsonResponse.ok) {
            throw new Error('Failed to load JSON');
        }
        
        plotData = await jsonResponse.json();
        
        const svgResponse = await fetch(urls.svg);
        if (!svgResponse.ok) {
            throw new Error('Failed to load SVG');
        }
        
        const svgText = await svgResponse.text();
        const container = $('svgContainer');
        container.innerHTML = svgText;
        attachSVGClickHandler();
        
        setPlotDetails('<div class="hint">Click a plot to see its dimensions and adjacency.</div>');
    } catch (error) {
        console.error('Error loading selected result:', error);
        setPlotDetails('Error loading result. Please try again.');
    }
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

    if (data.dimension) {
        html += `<p>North-South: ${data.dimension['north-south']}</p>`;
        html += `<p>East-West: ${data.dimension['east-west']}</p>`;
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

    svg.querySelectorAll('rect.plot-area').forEach((rect) => {
        rect.classList.remove('selected');
    });

    const selectedRect = svg.getElementById(id);
    if (selectedRect) {
        selectedRect.classList.add('selected');
    }
}

async function loadInteractiveSVG() {
    try {
        // Load plot data from adjacency JSON if not already loaded
        if (!plotData || Object.keys(plotData).length === 0) {
            const dataResponse = await fetch('/plot_adjacency_data.json');
            if (dataResponse.ok) {
                plotData = await dataResponse.json();
            }
        }

        const response = await fetch('/extracted_plots/extracted_plots.svg');
        if (!response.ok) {
            return;
        }

        const svgText = await response.text();
        const container = $('svgContainer');
        container.innerHTML = svgText;
        attachSVGClickHandler();
    } catch (error) {
        console.error('SVG load error', error);
    }
}

function openFullSvgPage() {
    window.location.href = '/svg-view';
}

function wireEvents() {
    const fileInput = getElement('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (!file) {
                return;
            }

            const reader = new FileReader();
            reader.onload = (e) => {
                const uploadedImage = getElement('uploadedImage');
                if (uploadedImage) {
                    uploadedImage.src = e.target.result;
                }
                showElement('imageContainer');
            };
            reader.readAsDataURL(file);

            uploadAndProcess(file);
        });
    }

    const plotSearch = getElement('plotSearch');
    if (plotSearch) {
        plotSearch.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                searchPlot();
            }
        });
    }

    const openSvgButton = getElement('openSvgButton');
    if (openSvgButton) {
        openSvgButton.addEventListener('click', openFullSvgPage);
    }

    const currentView = document.body?.dataset?.view || document.documentElement?.dataset?.view;

    if (currentView === 'svg-view') {
        populateResultsDropdown();
    } else {
        // Load and display saved results on analysis page
        loadSavedResults();
    }
}

window.searchPlot = searchPlot;
window.showAllPlots = showAllPlots;
window.loadInteractiveSVG = loadInteractiveSVG;
window.openFullSvgPage = openFullSvgPage;
window.loadSavedResults = loadSavedResults;
window.loadSavedResult = loadSavedResult;
window.attachSVGClickHandler = attachSVGClickHandler;

window.populateResultsDropdown = populateResultsDropdown;
window.loadSelectedResult = loadSelectedResult;

window.addEventListener('DOMContentLoaded', wireEvents);
