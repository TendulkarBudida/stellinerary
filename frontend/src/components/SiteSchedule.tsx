import React from 'react';
import type { Site, SiteWeatherForecast, ObservationSchedule } from '../types';

interface SiteScheduleProps {
    site: Site;
    weather: SiteWeatherForecast;
    schedule: ObservationSchedule;
}

const SiteSchedule: React.FC<SiteScheduleProps> = ({ site, weather, schedule }) => {
    return (
        <div className="card site-schedule">
            <div className="site-header">
                <h2>📍 {site.name}, {site.state}</h2>
                <div className="site-stats">
                    <span>Altitude: {site.altitude_m}m</span>
                    <span>Bortle Class: {site.bortle_class}</span>
                </div>
            </div>

            <div className="weather-summary">
                <h3>🌤️ Weather Outlook</h3>
                <p>{weather.summary}</p>
            </div>

            <div className="schedule-timeline">
                <h3>⏱️ Observation Choreography</h3>
                <div className="timeline-meta">
                    {schedule.astronomical_twilight_end && <span>True Dark Begins: {schedule.astronomical_twilight_end}</span>}
                    {schedule.moon_phase_pct !== undefined && <span>Moon Phase: {schedule.moon_phase_pct}%</span>}
                </div>
                
                <div className="timeline">
                    {schedule.entries.map((entry, idx) => (
                        <div key={idx} className={`timeline-entry ${entry.is_weather_dependent ? 'weather-dep' : ''}`}>
                            <div className="time-block">
                                <strong>{entry.time_local}</strong>
                                {entry.end_time_local && <span> - {entry.end_time_local}</span>}
                            </div>
                            <div className="entry-content">
                                <h4>{entry.title}</h4>
                                <p>{entry.description}</p>
                                {entry.direction && <span className="tag">Face {entry.direction}</span>}
                                {entry.altitude_deg !== undefined && <span className="tag">Alt: {entry.altitude_deg}°</span>}
                                {entry.dark_adaptation_note && <p className="warning">⚠️ {entry.dark_adaptation_note}</p>}
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default SiteSchedule;
