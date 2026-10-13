import React, { useState } from 'react';
import { motion } from 'motion/react';
import type { GearList, ObjectStory } from '../types';
import { Badge, Card, CardHeader } from './ui';

interface GearStoryProps {
  gear: GearList;
  stories: ObjectStory[];
}

const CATEGORY_LABEL: Record<string, string> = {
  essential: 'Essential',
  recommended: 'Recommended',
  optional: 'Optional',
};

const GearStory: React.FC<GearStoryProps> = ({ gear, stories }) => {
  const [checked, setChecked] = useState<Set<string>>(new Set());
  const [openStory, setOpenStory] = useState<string | null>(stories[0]?.event_id ?? null);

  const toggle = (name: string) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const total = gear.items.length;
  const done = gear.items.filter((i) => checked.has(i.name)).length;

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader
          title="Packing checklist"
          subtitle={total > 0 ? `${done} of ${total} packed` : undefined}
          right={total > 0 ? <Badge tone="info">{Math.round((done / total) * 100)}%</Badge> : undefined}
        />
        <div className="px-5 py-4 sm:px-6">
          {gear.warnings.length > 0 && (
            <div className="mb-4 space-y-2 rounded-xl border border-danger/30 bg-danger/5 p-3.5" role="alert">
              {gear.warnings.map((w, i) => (
                <p key={i} className="text-[13px] leading-relaxed text-danger">⚠ {w}</p>
              ))}
            </div>
          )}
          {['essential', 'recommended', 'optional'].map((category) => {
            const items = gear.items.filter((i) => i.category === category);
            if (items.length === 0) return null;
            return (
              <div key={category} className="mb-4 last:mb-0">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-accent">
                  {CATEGORY_LABEL[category] ?? category}
                </h3>
                <ul className="space-y-1.5">
                  {items.map((item) => (
                    <li key={item.name}>
                      <label
                        className={`flex cursor-pointer items-start gap-2.5 rounded-lg border px-3 py-2 text-sm transition-colors ${
                          checked.has(item.name)
                            ? 'border-success/30 bg-success/5 text-starfaint line-through'
                            : 'border-space-600/60 bg-space-950/50 text-stardim hover:border-accent/40'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={checked.has(item.name)}
                          onChange={() => toggle(item.name)}
                          className="mt-0.5 h-4 w-4 shrink-0 accent-[#34d399]"
                        />
                        <span>
                          <strong className="font-medium text-starlight">{item.name}</strong>
                          <span className="text-stardim"> — {item.reason}</span>
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </Card>

      <Card>
        <CardHeader title="Cosmic context" subtitle="The science behind your targets" />
        <div className="px-5 py-4 sm:px-6">
          {stories.length === 0 ? (
            <p className="text-sm text-stardim">No stories were generated for this trip.</p>
          ) : (
            <div className="space-y-2.5">
              {stories.map((story) => {
                const open = openStory === story.event_id;
                return (
                  <div key={story.event_id} className="overflow-hidden rounded-xl border border-space-600/60">
                    <button
                      type="button"
                      onClick={() => setOpenStory(open ? null : story.event_id)}
                      aria-expanded={open}
                      className="flex w-full items-center justify-between gap-3 bg-space-950/60 px-4 py-3 text-left"
                    >
                      <span className="font-display text-sm font-semibold text-starlight">{story.title}</span>
                      <span aria-hidden="true" className="text-accent">{open ? '−' : '+'}</span>
                    </button>
                    {open && (
                      <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="border-t border-space-600/50 px-4 py-3 text-sm leading-relaxed text-stardim"
                      >
                        {story.story_text}
                      </motion.p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default GearStory;
