import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Card } from './ui';

const STAGES = [
  { title: 'Curator', body: 'Ranking what is worth seeing on your dates' },
  { title: 'Location Scout', body: 'Scoring dark-sky sites against your limits' },
  { title: 'Weather', body: 'Checking astronomy forecasts for your site' },
  { title: 'Choreographer', body: 'Timing each target against terrain and twilight' },
  { title: 'Fallbacks', body: 'Packaging Plans A, B, and C with tradeoffs' },
  { title: 'Stories', body: 'Writing the science behind each event' },
];

/** Staged progress display for the long synchronous plan call. */
export default function LoadingJourney() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const id = window.setInterval(() => {
      setActive((a) => (a < STAGES.length - 1 ? a + 1 : a));
    }, 9000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <Card className="mx-auto max-w-2xl p-6 sm:p-8">
      <div className="flex items-center gap-3">
        <motion.span
          aria-hidden="true"
          className="text-2xl text-accent"
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 6, ease: 'linear' }}
        >
          ✦
        </motion.span>
        <div>
          <h2 className="font-display text-xl font-semibold text-starlight">Charting your sky…</h2>
          <p className="text-sm text-stardim">This takes about a minute — weather and stories are fetched live.</p>
        </div>
      </div>
      <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-space-700">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-accent2 to-accent"
          animate={{ width: `${((active + 1) / STAGES.length) * 100}%` }}
          transition={{ duration: 0.6 }}
        />
      </div>
      <ol className="mt-6 space-y-3">
        {STAGES.map((stage, i) => (
          <li key={stage.title} className="flex items-start gap-3">
            <span
              aria-hidden="true"
              className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${
                i < active ? 'bg-accent' : i === active ? 'animate-pulse bg-accent' : 'bg-space-600'
              }`}
            />
            <div>
              <p className={`font-display text-sm font-semibold ${i <= active ? 'text-starlight' : 'text-starfaint'}`}>
                {i + 1}. {stage.title}
              </p>
              <p className="text-xs text-stardim">{stage.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
