const express = require('express');
const fetch = require('node-fetch');
const { performance } = require('perf_hooks');

function createStandardRoutes(apiKey) {
    const router = express.Router();

    router.get('/weather', async (req, res) => {
        const startTime = performance.now();
        const { location } = req.query;

        if (!location) {
            return res.status(400).json({ error: 'Location query parameter is required.' });
        }

        const fullUrl = `https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/${location}/next5days?unitGroup=metric&key=${apiKey}&contentType=json`;

        try {
            const apiResponse = await fetch(fullUrl);
            const data = await apiResponse.json();

            if (!apiResponse.ok) {
                throw new Error(data.message || 'API request failed');
            }

            const endTime = performance.now();
            res.json({
                success: true,
                data: data,
                backendProcessingTime: endTime - startTime
            });
        } catch (error) {
            const endTime = performance.now();
            res.status(500).json({
                success: false,
                error: { message: 'Failed to fetch weather data.', details: error.message },
                backendProcessingTime: endTime - startTime
            });
        }
    });

    return router;
}

module.exports = { createStandardRoutes };