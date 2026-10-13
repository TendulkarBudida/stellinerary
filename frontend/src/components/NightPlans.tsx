import React from 'react';
import { motion } from 'motion/react';
import type { NightPlan, Site } from '../types';
import { Badge, Card, CardHeader, ConfidenceBadge, MoonPhase } from './ui';

interface NightPlansProps {
  site: Site;
  nights: NightPlan[];
}

const NightPlans: React.FC<NightPlansProps> = ({ site, nights }) => (
  <Card>
    <CardHeader
      title={`Night timeline · ${site.name}`}
      subtitle={site.state}
      right={
        <div className="flex gap-2">
          <Badge tone="neutral">{site.altitude_m} m</Badge>
          <Badge tone="info">Bortle {site.bortle_class}</Badge>
        </div>
      }
    />

    {nights.map((night) => (
      <section key={night.observation_date} className="border-b border-space-600/40 px-5 py-5 last:border-0 sm:px-6">
        <div className="flex flex-wrap items-center gap-2.5">
          <h3 className="font-display text-base font-semibold text-starlight">
            {new Date(`${night.observation_date}T12:00:00`).toLocaleDateString(undefined, {
              weekday: 'long',
              month: 'long',
              day: 'numeric',
            })}
          </h3>
          <ConfidenceBadge confidence={night.forecast_confidence} />
        </div>
        {night.weather_forecast?.summary && (
          <p className="mt-1.5 text-sm text-stardim">{night.weather_forecast.summary}</p>
        )}
        {night.reasons.map((reason) => (
          <p key={reason} className="mt-1 text-xs text-starfaint">• {reason}</p>
        ))}

        {night.schedule && (
          <>
            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-stardim">
              {night.schedule.astronomical_twilight_end && (
                <span>True dark from <strong className="text-accent">{night.schedule.astronomical_twilight_end}</strong></span>
              )}
              {night.schedule.astronomical_twilight_start && (
                <span>until <strong className="text-accent">{night.schedule.astronomical_twilight_start}</strong></span>
              )}
              <MoonPhase phasePct={night.schedule.moon_phase_pct} />
            </div>
            <ol className="relative mt-4 space-y-0 border-l border-space-600 pl-0">
              {night.schedule.entries.map((entry, index) => (
                <motion.li
                  key={`${night.observation_date}-${index}`}
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: '-20px' }}
                  transition={{ duration: 0.3 }}
                  className="relative pb-5 pl-6 last:pb-0"
                >
                  <span
                    aria-hidden="true"
                    className={`absolute -left-[5px] top-1.5 h-2.5 w-2.5 rounded-full ${
                      entry.is_weather_dependent ? 'bg-warn' : 'bg-accent'
                    } shadow-[0_0_10px_rgba(103,232,249,0.6)]`}
                  />
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="font-mono text-sm font-semibold text-accent">
                      {entry.time_local}
                      {entry.end_time_local && <span className="text-starfaint"> – {entry.end_time_local}</span>}
                    </span>
                    {entry.is_weather_dependent && <Badge tone="warn">needs clear sky</Badge>}
                  </div>
                  <h4 className="mt-1 font-display text-[15px] font-semibold text-starlight">{entry.title}</h4>
                  <p className="mt-0.5 max-w-3xl text-sm leading-relaxed text-stardim">{entry.description}</p>
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {entry.direction && <Badge tone="info">Face {entry.direction}</Badge>}
                    {entry.altitude_deg !== undefined && <Badge tone="neutral">Alt {entry.altitude_deg}°</Badge>}
                  </div>
                  {entry.dark_adaptation_note && (
                    <p className="mt-1.5 text-xs text-danger">⚠ {entry.dark_adaptation_note}</p>
                  )}
                </motion.li>
              ))}
            </ol>
          </>
        )}
      </section>
    ))}
  </Card>
);

export default NightPlans;
