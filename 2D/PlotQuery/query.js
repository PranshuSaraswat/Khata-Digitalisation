const express = require('express');
const { GoogleGenerativeAI } = require('@google/generative-ai');
require('dotenv').config();

const app = express();
app.use(express.json());

// Initialize the Gemini API client
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

const plots = [
  { plotNo: 1, x: 0, y: 0, width: 120, height: 100, facing: { N: 30, S: 210, E: 90, W: 270 } },
  { plotNo: 2, x: 120, y: 0, width: 100, height: 100, facing: { N: 45, S: 225, E: 135, W: 315 } },
  { plotNo: 3, x: 220, y: 0, width: 120, height: 100, facing: { N: 60, S: 240, E: 150, W: 330 }}, 
  { plotNo: 4, x: 340, y: 0, width: 260, height: 100, facing: { N: 90, S: 270, E: 190, W: 400 }},
  { plotNo: 5, x: 0, y: 150, width: 150, height: 90, facing: { N: 120, S: 300, E: 210, W: 30 } },
  { plotNo: 6, x: 150, y: 150, width: 200, height: 90, facing: { N: 150, S: 330, E: 240, W: 60 } },
  { plotNo: 7, x: 350, y: 150, width: 250, height: 90, facing: { N: 180, S: 360, E: 270, W: 90 } },
  { plotNo: 8, x: 0, y: 240, width: 150, height: 110, facing: { N: 165, S: 360, E: 270, W: 90 } },
  { plotNo: 9, x: 150, y: 240, width: 200, height: 110, facing: { N: 175, S: 360, E: 270, W: 90 } },
  { plotNo: 10, x: 350, y: 240, width: 250, height: 110, facing: { N: 195, S: 360, E: 270, W: 90 } },
  { plotNo: 11, x: 0, y: 425, width: 200, height: 200, facing: { N: 210, S: 30, E: 300, W: 120 } },
  { plotNo: 9, x: 200, y: 425, width: 200, height: 200, facing: { N: 240, S: 60, E: 330, W: 150 } },
  { plotNo: 10, x: 400, y: 425, width: 200, height: 200, facing: { N: 270, S: 90, E: 360, W: 180 } }
];

// Road data
const roads = [
  { name:"30 feet Road",x: 0, y: 350, width: 600, height: 75 },
  { name:"10 feet Road",x: 0, y: 100, width: 600, height: 50 }
];

app.post('/query', async (req, res) => {
  const { question } = req.body;
  
  try {
    // Use Gemini 1.5 Flash model
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });
    
    // Prepare the system message and user query
    const systemMessage = "You are a helpful assistant that analyzes plots and roads in a layout. Answer based on the given JSON data.";
    const userQuery = `Plots:\n${JSON.stringify(plots, null, 2)}\n\nRoads:\n${JSON.stringify(roads, null, 2)}\n\nUser query: ${question}`;
    
    // Generate content with the model directly
    const result = await model.generateContent([
      systemMessage,
      userQuery
    ]);
    
    const response = result.response;
    
    res.json({ answer: response.text() });
  } catch (error) {
    console.error('Error querying API:', error);
    res.status(500).json({ error: 'Failed to process your request' });
  }
});

app.listen(3000, () => {
  console.log('Server listening on http://localhost:3000');
});