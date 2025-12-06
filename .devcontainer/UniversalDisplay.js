import React, { useState, useEffect } from 'react';

function UniversalDisplay() {
    const [scene, setScene] = useState(null);

    const renderComponent = (component) => {
        const style = {
            position: 'absolute',
            ...component.style
        };

        const props = {
            key: component.id,
            id: component.id,
            style: style,
            'data-clickable-id': component.clickable_id,
            ...(component.clickable_id && { style: { ...style, cursor: 'pointer' } })
        };

        switch (component.type) {
            case 'text':
                return <div {...props}>{component.content}</div>;
            case 'image':
                return <img src={component.src} alt={component.id} {...props} />;
            case 'canvas':
                return <canvas
                    {...props}
                    ref={canvas => {
                        if (canvas && component.drawing_instructions) {
                            const ctx = canvas.getContext('2d');
                            canvas.width = parseInt(component.style.width);
                            canvas.height = parseInt(component.style.height);
                            component.drawing_instructions.forEach(instr => {
                                ctx.fillStyle = instr.color;
                                if (instr.shape === 'rect') {
                                    ctx.fillRect(...instr.params);
                                } else if (instr.shape === 'text') {
                                    ctx.font = instr.font;
                                    ctx.fillText(instr.content, ...instr.params);
                                }
                            });
                        }
                    }}
                />;
            default:
                return null;
        }
    };

    const fetchAndRenderScene = () => {
        fetch('http://localhost:5001/scene')
            .then(response => response.json())
            .then(data => setScene(data.scene))
            .catch(error => console.error("Error fetching scene:", error));
    };

    useEffect(() => {
        fetchAndRenderScene();
    }, []);

    const handleContainerClick = (event) => {
        if (event.target.dataset.clickableId) {
            fetchAndRenderScene();
        }
    };

    return (
        <div style={{ textAlign: 'center', padding: '2em' }}>
            <h1 style={{ color: '#0d6efd' }}>Universal Display</h1>
            <div
                id="universal-display-container"
                style={scene ? { maxWidth: '800px', margin: 'auto', ...scene.containerStyle } : {}}
                onClick={handleContainerClick}
            >
                {scene && scene.components.map(renderComponent)}
            </div>
        </div>
    );
}

export default UniversalDisplay;