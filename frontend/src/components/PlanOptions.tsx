import React, { useState } from 'react';
import { motion } from 'motion/react';
import type { PlanOption } from '../types';
import { Badge, Card, CardHeader, ConfidenceBadge, ScoreBars } from './ui';
import NightPlans from './NightPlans';
import GearStory from './GearStory';

interface PlanOptionsProps {
  options: PlanOption[];
  rankedSites: { site: { id: string }; distance_km: number; score_components: Record<string, number> }[];
  stories: Parameters<typeof GearStory>[0]['stories'];
}

const META: Record<PlanOption['label'], { title: string; blurb: string }> = {
  primary: { title: 'Plan A', blurb: 'Recommended' },
  weather_fallback: { title: 'Plan B', blurb: 'If Plan A weather fails' },
  local_fallback: { title: 'Plan C', blurb: 'Closer, simpler outing' },
};

const PlanOptions: React.FC<PlanOptionsProps> = ({ options, rankedSites, stories }) => {
  const [selected, setSelected] = useState(0);
  const option = options[selected];
  if (!option) return null;

  const ranked = rankedSites.find((r) => r.site.id === option.site.id);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title="Choose your trip plan" subtitle="Each option carries its own schedule, forecast, and packing list" />
        <div className="grid gap-3 p-5 sm:grid-cols-3 sm:px-6" role="tablist" aria-label="Trip plan options">
          {options.map((candidate, index) => {
            const active = index === selected;
            return (
              <button
                key={candidate.label}
                role="tab"
                aria-selected={active}
                onClick={() => setSelected(index)}
                className={`rounded-xl border p-4 text-left transition-all ${
                  active
                    ? 'border-accent bg-accent/10 shadow-[0_0_24px_rgba(103,232,249,0.15)]'
                    : 'border-space-600 bg-space-950/60 hover:border-accent/40'
                }`}
              >
                <p className="font-display text-sm font-bold text-accent">{META[candidate.label].title}</p>
                <p className="mt-0.5 text-sm font-semibold text-starlight">{candidate.site.name}</p>
                <p className="mt-0.5 text-xs text-starfaint">{META[candidate.label].blurb}</p>
                <p className="mt-2 font-mono text-xs text-stardim">score {Math.round(candidate.score * 100)}</p>
              </button>
            );
          })}
        </div>
      </Card>

      <motion.div
        key={option.label}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="space-y-4"
      >
        <Card className="p-5 sm:p-6">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-lg font-semibold text-starlight">
              {META[option.label].title} — {option.site.name}
            </h3>
            <ConfidenceBadge confidence={option.confidence} />
            {option.site.bortle_class != null && <Badge tone="neutral">Bortle {option.site.bortle_class}</Badge>}
          </div>
          <ul className="mt-3 space-y-1.5">
            {option.reasons.map((reason) => (
              <li key={reason} className="flex gap-2 text-sm text-stardim">
                <span aria-hidden="true" className="text-success">✓</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
          {option.tradeoffs.length > 0 && (
            <div className="mt-3 rounded-lg border border-warn/30 bg-warn/5 p-3">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-warn">Tradeoffs</p>
              <ul className="space-y-1">
                {option.tradeoffs.map((tradeoff) => (
                  <li key={tradeoff} className="break-words text-sm text-warn/90">• {tradeoff}</li>
                ))}
              </ul>
            </div>
          )}
          {ranked && Object.keys(ranked.score_components).length > 0 && (
            <div className="mt-4 max-w-md">
              <ScoreBars components={ranked.score_components} />
            </div>
          )}
        </Card>

        <NightPlans site={option.site} nights={[option.night_plan]} />
        <GearStory gear={option.gear} stories={stories} />
      </motion.div>
    </div>
  );
};

export default PlanOptions;
