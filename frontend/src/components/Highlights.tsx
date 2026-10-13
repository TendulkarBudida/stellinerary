import { motion } from 'motion/react';
import type { CelestialEvent } from '../types';
import { Card, CardHeader } from './ui';

interface HighlightsProps {
  events: CelestialEvent[];
}

const TYPE_ICON: Record<string, string> = {
  meteor_shower: '☄',
  opposition: '♃',
  elongation: '☿',
  eclipse: '◍',
  seasonal: '✦',
};

const Highlights: React.FC<HighlightsProps> = ({ events }) => {
  if (!events || events.length === 0) {
    return (
      <Card>
        <CardHeader title="Cosmic highlights" subtitle="No major events in this window" />
        <p className="px-5 py-4 text-sm text-stardim sm:px-6">
          Nothing headline-worthy overlaps your dates — but dark skies, planets, and the Milky Way are always there.
        </p>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title="Cosmic highlights" subtitle={`${events.length} ranked event${events.length > 1 ? 's' : ''} in your window`} />
      <div className="grid gap-3 p-5 sm:grid-cols-2 sm:px-6">
        {events.map((event, i) => (
          <motion.article
            key={event.id}
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-30px' }}
            transition={{ duration: 0.4, delay: (i % 2) * 0.07 }}
            className="rounded-xl border border-space-600/70 bg-space-950/70 p-4"
          >
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-display text-base font-semibold text-starlight">
                <span aria-hidden="true" className="mr-2 text-accent">{TYPE_ICON[event.type] ?? '✦'}</span>
                {event.name}
              </h3>
            </div>
            <p className="mt-1 text-[11px] font-medium uppercase tracking-wider text-accent/80">
              {event.type.replace(/_/g, ' ')}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-stardim">{event.description}</p>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-starfaint">
              {event.zhr != null && <span>ZHR {event.zhr}</span>}
              <span>Peak {new Date(event.peak_date).toLocaleDateString()}</span>
              {event.best_hours && <span>{event.best_hours}</span>}
            </div>
          </motion.article>
        ))}
      </div>
    </Card>
  );
};

export default Highlights;
