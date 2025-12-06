import React, { useState, useEffect } from 'react';

const sidebarStyle = {
    width: '300px',
    backgroundColor: '#343a40',
    padding: '1em',
    overflowY: 'auto',
    borderRight: '2px solid #495057',
    height: '100vh',
};

const mainContentStyle = {
    flexGrow: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
};

const gameRendererStyle = {
    flexGrow: 1,
    border: 'none',
    backgroundColor: '#000',
};

const searchBarStyle = {
    width: 'calc(100% - 20px)',
    padding: '10px',
    marginBottom: '1em',
    borderRadius: '4px',
    border: '1px solid #495057',
    backgroundColor: '#212529',
    color: '#f8f9fa',
};

const gameItemStyle = {
    padding: '10px',
    marginBottom: '5px',
    borderRadius: '4px',
    cursor: 'pointer',
    backgroundColor: '#495057',
    transition: 'background-color 0.2s',
};


function DemoPage() {
    const [allGames, setAllGames] = useState([]);
    const [filteredGames, setFilteredGames] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchGames = async () => {
            const gamesApiUrl = 'https://www.freetogame.com/api/games';
            const proxyUrl = `http://localhost:5001/proxy?url=${encodeURIComponent(gamesApiUrl)}`;

            try {
                const response = await fetch(proxyUrl);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const games = await response.json();
                setAllGames(games);
                setFilteredGames(games.slice(0, 50)); // Initially show first 50
                setLoading(false);
            } catch (e) {
                setError('Failed to load games.');
                setLoading(false);
                console.error('Error fetching game data:', e);
            }
        };

        fetchGames();
    }, []);

    const handleSearch = (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const filtered = allGames.filter(game => game.title.toLowerCase().includes(searchTerm));
        setFilteredGames(filtered.slice(0, 50));
    };

    const handleGameClick = (gameUrl) => {
        const iframe = document.getElementById('game-renderer');
        if (iframe) {
            iframe.src = gameUrl;
        }
    };

    return (
        <div style={{ display: 'flex', height: '100vh', backgroundColor: '#212529', color: '#f8f9fa' }}>
            <div id="sidebar" style={sidebarStyle}>
                <h1 style={{ color: '#0d6efd', textAlign: 'center' }}>Free Games</h1>
                <input type="text" id="search-bar" placeholder="Search for a game..." style={searchBarStyle} onChange={handleSearch} />
                <div id="game-list">
                    {loading && <p>Loading games...</p>}
                    {error && <p>{error}</p>}
                    {filteredGames.map(game => (
                        <div key={game.id} className="game-item" style={gameItemStyle} onMouseOver={e => e.currentTarget.style.backgroundColor = '#0d6efd'} onMouseOut={e => e.currentTarget.style.backgroundColor = '#495057'} onClick={() => handleGameClick(game.game_url)}>
                            {game.title}
                        </div>
                    ))}
                </div>
            </div>
            <div id="main-content" style={mainContentStyle}>
                <iframe id="game-renderer" title="Game Renderer" style={gameRendererStyle}></iframe>
            </div>
        </div>
    );
}

export default DemoPage;