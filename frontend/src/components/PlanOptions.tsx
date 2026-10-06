import React, { useState } from 'react';
import type { PlanOption } from '../types';
import NightPlans from './NightPlans';
import GearStory from './GearStory';

interface PlanOptionsProps {
    options: PlanOption[];
    stories: Parameters<typeof GearStory>[0]['stories'];
}

const titles: Record<PlanOption['label'], string> = {
    primary: 'Plan A — Recommended',
    weather_fallback: 'Plan B — Weather Fallback',
    local_fallback: 'Plan C — Local Fallback',
};

const PlanOptions: React.FC<PlanOptionsProps> = ({ options, stories }) => {
    const [selected, setSelected] = useState(0);
    const option = options[selected];
    if (!option) return null;

    return (
        <>
            <div className="card">
                <h2>Choose your trip plan</h2>
                <div className="event-grid">
                    {options.map((candidate, index) => (
                        <button key={candidate.label} className="btn-secondary" onClick={() => setSelected(index)}>
                            {titles[candidate.label]}: {candidate.site.name}
                        </button>
                    ))}
                </div>
                <h3>{titles[option.label]}</h3>
                {option.reasons.map((reason) => <p key={reason}>{reason}</p>)}
                {option.tradeoffs.map((tradeoff) => <p className="warning" key={tradeoff}>{tradeoff}</p>)}
            </div>
            <NightPlans site={option.site} nights={[option.night_plan]} />
            <GearStory gear={option.gear} stories={stories} />
        </>
    );
};

export default PlanOptions;
