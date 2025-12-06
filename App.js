import React, { useState } from 'react';
import './App.css';

// This function analyzes the JSON data to generate a detailed report.
const generateReport = (reportData, jsonData) => {
  if (!reportData && !jsonData) return null;

  const analysis = {
    invocationChain: reportData || [],
    dataSummary: {
      totalKeys: 0,
      topLevelKeys: [],
      dataTypes: new Set(),
    },
    provenance: [],
  };

  // Analyze the JSON data structure
  if (jsonData) {
    const keys = Object.keys(jsonData);
    analysis.dataSummary.totalKeys = keys.length;
    analysis.dataSummary.topLevelKeys = keys;

    keys.forEach(key => {
      const value = jsonData[key];
      const type = typeof value;
      if (type === 'object' && value !== null && !Array.isArray(value)) {
        analysis.dataSummary.dataTypes.add('object');
      } else if (Array.isArray(value)) {
        analysis.dataSummary.dataTypes.add('array');
      } else {
        analysis.dataSummary.dataTypes.add(type);
      }
    });
  }

  // Map invocation chain to data provenance
  if (reportData && jsonData) {
    reportData.forEach(pointer => {
      let keysFromPointer = [];
      if (pointer.description.toLowerCase().includes('user profile')) {
        keysFromPointer = ['user_id', 'name'];
      } else if (pointer.description.toLowerCase().includes('contact info')) {
        keysFromPointer = ['email'];
      } else if (pointer.description.toLowerCase().includes('facebook')) {
        keysFromPointer = ['external_profile'];
      } else if (pointer.description.toLowerCase().includes('crypto')) {
        keysFromPointer = ['crypto_price'];
      }
      
      const foundKeys = keysFromPointer.filter(key => jsonData.hasOwnProperty(key));
      if(foundKeys.length > 0) {
        analysis.provenance.push({
          description: pointer.description,
          address: pointer.address,
          providedKeys: foundKeys,
        });
      }
    });
  }

  return analysis;
};

function App() {
  const [apiToken, setApiToken] = useState('');
  const [query, setQuery] = useState('get with neighbors');
  const [result, setResult] = useState(null);
  const [report, setReport] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleInvoke = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setResult(null);
    setReport(null);

    try {
      const formData = new URLSearchParams();
      formData.append('api_token', apiToken);
      // In the future, the query could be passed here too.
      // formData.append('query', query);

      const response = await fetch('http://127.0.0.1:5001/invoke', {
        method: 'POST',
        body: formData,
      });

      const responseData = await response.json();

      if (!response.ok) {
        throw new Error(responseData.error || 'An unknown error occurred.');
      }

      setResult(responseData.data);
      setReport(generateReport(responseData.report, responseData.data));

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Butterfly Effect - React UI</h1>
        <p>A universal connector for applications and datastores.</p>
      </header>
      <main>
        <div className="card">
          <h2>Invocation Control</h2>
          <form onSubmit={handleInvoke}>
            <div className="form-group">
              <label htmlFor="api-token">Connection String (API Token)</label>
              <input
                type="text"
                id="api-token"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder="Paste your Facebook API Token here"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="query">Query</label>
              <input
                type="text"
                id="query"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g., get with neighbors"
                required
              />
            </div>
            <button type="submit" disabled={isLoading}>
              {isLoading ? 'Invoking...' : 'Invoke Pointers'}
            </button>
          </form>
        </div>

        {error && <div className="card error-card"><p>{error}</p></div>}

        <div className="results-container">
          <div className="card result-card">
            <h2>Raw JSON Result</h2>
            <pre>{result ? JSON.stringify(result, null, 2) : '{ "status": "Awaiting invocation..." }'}</pre>
          </div>

          {report && (
            <div className="card report-card">
              <h2>Detailed Report</h2>
              
              <h3>Invocation Chain</h3>
              <ul>
                {report.invocationChain.map((p, i) => <li key={i}><strong>{p.description}</strong> ({p.address})</li>)}
              </ul>

              <h3>Data Provenance</h3>
              <p>Shows which pointer provided which top-level keys in the result.</p>
              <ul>
                {report.provenance.map((p, i) => (
                  <li key={i}>
                    <strong>{p.description}:</strong>
                    <span> Provided [ {p.providedKeys.join(', ')} ]</span>
                  </li>
                ))}
              </ul>

              <h3>Data Summary</h3>
              <ul>
                <li><strong>Total Top-Level Keys:</strong> {report.dataSummary.totalKeys}</li>
                <li><strong>Top-Level Keys:</strong> {report.dataSummary.topLevelKeys.join(', ')}</li>
                <li><strong>Data Types Found:</strong> {[...report.dataSummary.dataTypes].join(', ')}</li>
              </ul>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;