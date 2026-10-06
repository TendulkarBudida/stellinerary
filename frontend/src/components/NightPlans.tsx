import React from 'react';
import type { NightPlan, Site } from '../types';

interface NightPlansProps {
    site: Site;
    nights: NightPlan[];
}

const confidenceLabel = (night: NightPlan): string => {
    if (night.forecast_confidence === 'unavailable_outside_horizon') {
        return 'Weather forecast is not available for this night yet. Recheck closer to the trip.';
    }
    if (night.forecast_confidence === 'unavailable_provider_error') {
        return 'Weather data is currently unavailable. Verify local conditions before travelling.';
    }
    return night.weather_forecast?.summary || 'Weather forecast covers this observing night.';
};

const NightPlans: React.FC<NightPlansProps> = ({ site, nights }) => (
    <div className="card site-schedule">
        <div className="site-header">
            <h2>Observation plans for {site.name}, {site.state}</h2>
            <div className="site-stats">
                <span>Altitude: {site.altitude_m}m</span>
                <span>Bortle Class: {site.bortle_class}</span>
            </div>
        </div>

        {nights.map((night) => (
            <section key={night.observation_date} className="schedule-timeline">
                <h3>{new Date(`${night.observation_date}T12:00:00`).toLocaleDateString()}</h3>
                <p className={night.forecast_confidence.startsWith('unavailable') ? 'warning' : ''}>
                    {confidenceLabel(night)}
                </p>
                {night.reasons.map((reason) => <p key={reason}>{reason}</p>)}

                {night.schedule && (
                    <>
                        <div className="timeline-meta">
                            {night.schedule.astronomical_twilight_end && <span>True Dark Begins: {night.schedule.astronomical_twilight_end}</span>}
                            {night.schedule.moon_phase_pct !== undefined && <span>Moon Phase: {night.schedule.moon_phase_pct}%</span>}
                        </div>
                        <div className="timeline">
                            {night.schedule.entries.map((entry, index) => (
                                <div key={`${night.observation_date}-${index}`} className={`timeline-entry ${entry.is_weather_dependent ? 'weather-dep' : ''}`}>
                                    <div className="time-block">
                                        <strong>{entry.time_local}</strong>
                                        {entry.end_time_local && <span> - {entry.end_time_local}</span>}
                                    </div>
                                    <div className="entry-content">
                                        <h4>{entry.title}</h4>
                                        <p>{entry.description}</p>
                                        {entry.direction && <span className="tag">Face {entry.direction}</span>}
                                        {entry.altitude_deg !== undefined && <span className="tag">Alt: {entry.altitude_deg}°</span>}
                                        {entry.dark_adaptation_note && <p className="warning">{entry.dark_adaptation_note}</p>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </section>
        ))}
    </div>
);

export default NightPlans;
