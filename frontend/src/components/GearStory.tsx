import React from 'react';
import type { GearList, ObjectStory } from '../types';

interface GearStoryProps {
    gear: GearList;
    stories: ObjectStory[];
}

const GearStory: React.FC<GearStoryProps> = ({ gear, stories }) => {
    return (
        <div className="gear-story-container">
            <div className="card gear-panel">
                <h2>🎒 Packing List</h2>
                
                {gear.warnings && gear.warnings.length > 0 && (
                    <div className="gear-warnings">
                        {gear.warnings.map((w, i) => (
                            <p key={i}>⚠️ {w}</p>
                        ))}
                    </div>
                )}

                <div className="gear-categories">
                    {['essential', 'recommended', 'optional'].map(category => {
                        const items = gear.items.filter(i => i.category === category);
                        if (items.length === 0) return null;
                        return (
                            <div key={category} className="gear-category">
                                <h3>{category.toUpperCase()}</h3>
                                <ul>
                                    {items.map((item, idx) => (
                                        <li key={idx}>
                                            <strong>{item.name}</strong> - {item.reason}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="card story-panel">
                <h2>📖 Cosmic Context</h2>
                {stories.length === 0 ? (
                    <p>No stories generated for this trip.</p>
                ) : (
                    <div className="stories-list">
                        {stories.map((story, idx) => (
                            <div key={idx} className="story-item">
                                <h3>{story.title}</h3>
                                <p className="story-text">{story.story_text}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default GearStory;
