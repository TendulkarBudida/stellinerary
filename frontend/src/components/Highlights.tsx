import React from 'react';
import type { CelestialEvent } from '../types';

interface HighlightsProps {
    events: CelestialEvent[];
}

const Highlights: React.FC<HighlightsProps> = ({ events }) => {
    if (!events || events.length === 0) {
        return (
            <div className="card">
                <h2>No Major Events</h2>
                <p>No highly ranked celestial events during this window. But the night sky is always beautiful!</p>
            </div>
        );
    }

    return (
        <div className="card highlights">
            <h2>Cosmic Highlights</h2>
            <div className="event-grid">
                {events.map((event) => (
                    <div key={event.id} className="event-card">
                        <h3>{event.name}</h3>
                        <p className="event-type">{event.type.replace('_', ' ')}</p>
                        <p className="event-desc">{event.description}</p>
                        <div className="event-meta">
                            {event.zhr && <span>ZHR: {event.zhr}</span>}
                            <span>Peak: {new Date(event.peak_date).toLocaleDateString()}</span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Highlights;
