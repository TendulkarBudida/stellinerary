import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import Starfield from '../components/Starfield';
import { Button, Card, SectionHeading } from '../components/ui';

const fadeUp = {
  initial: { opacity: 0, y: 28 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: '-60px' },
  transition: { duration: 0.6, ease: 'easeOut' as const },
};

const STEPS = [
  { n: '01', title: 'Curator', body: 'Ranks what is actually worth seeing on your dates — meteor peaks, oppositions, eclipses, Milky Way season — filtered by moon interference and sky darkness.' },
  { n: '02', title: 'Location Scout', body: 'Scores dark-sky sites on event visibility, weather, darkness, and drive time — against your travel limits, not just raw darkness.' },
  { n: '03', title: 'Weather check', body: 'Pulls an astronomy forecast for your site. If the forecast does not cover your night, the plan says so instead of guessing.' },
  { n: '04', title: 'Choreographer', body: 'Builds a minute-by-minute timeline: when each target clears the terrain, when true dark begins, what the moon does.' },
  { n: '05', title: 'Plans A, B, C', body: 'A recommended trip plus a weather fallback and a closer local fallback — each with its own schedule and packing list.' },
  { n: '06', title: 'Gear + stories', body: 'A packing list tuned to temperature, altitude, and humidity, plus the science stories behind what you will see.' },
];

const DELIVERABLES = [
  { title: 'Where + which night', body: 'A ranked site and the best night in your range, with the score parts shown — visibility, weather, darkness, distance.' },
  { title: 'Exact timeline', body: 'Dark-adaptation start, true-dark hours, moon times, and per-target viewing windows with compass directions.' },
  { title: 'Backup plans', body: 'What triggers a switch to Plan B, and what you give up or gain with each alternative.' },
  { title: 'Packing + safety', body: 'Cold, altitude, dew, trek, and eclipse warnings generated from your site and forecast — not generic tips.' },
];

const SITES = [
  { name: 'Hanle, Ladakh', meta: 'Bortle 1 · 4,500 m' },
  { name: 'Spiti Valley', meta: 'Bortle 1 · 4,200 m' },
  { name: 'Rann of Kutch', meta: 'Bortle 2 · flat horizon' },
  { name: 'Coorg', meta: 'Bortle 3 · weekend trip' },
  { name: 'Nandi Hills', meta: 'Bortle 4 · 60 km from Bangalore' },
  { name: 'Horsley Hills', meta: 'Bortle 4 · resort stay' },
];

export default function Landing() {
  return (
    <div>
      {/* ── Hero ─────────────────────────────────────────── */}
      <section className="relative overflow-hidden rounded-3xl border border-space-600/50 bg-space-900/60 px-6 py-20 text-center sm:px-12 sm:py-28">
        <div className="absolute inset-0">
          <Starfield density={1.4} />
        </div>
        <div className="relative">
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-4 font-display text-xs font-semibold uppercase tracking-[0.3em] text-accent"
          >
            Night-sky expedition planner
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.08 }}
            className="mx-auto max-w-3xl font-display text-4xl font-bold leading-tight text-starlight sm:text-6xl"
          >
            Where should you go, on which night, at what time?
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.16 }}
            className="mx-auto mt-5 max-w-xl text-base text-stardim sm:text-lg"
          >
            Stellinerary weighs your constraints, the sky calendar, terrain, and
            weather — then hands you a primary plan, a backup, and a packing list.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.65, delay: 0.24 }}
            className="mx-auto mt-8 flex max-w-md flex-col items-stretch justify-center gap-3 sm:max-w-none sm:flex-row sm:items-center"
          >
            <Link to="/plan" className="w-full sm:w-auto">
              <Button className="w-full sm:w-auto">Plan an expedition</Button>
            </Link>
            <a href="#how" className="w-full sm:w-auto">
              <Button variant="ghost" className="w-full sm:w-auto">How it works</Button>
            </a>
          </motion.div>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="mt-10 flex flex-wrap items-center justify-center gap-2 text-xs text-stardim"
          >
            {['10 curated dark-sky sites', '6-step planning pipeline', 'Plan A · B · C output', 'Forecast-honest scheduling'].map((chip) => (
              <span key={chip} className="rounded-full border border-space-600 bg-space-950/70 px-3 py-1.5">
                {chip}
              </span>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────── */}
      <section id="how" className="scroll-mt-24 pt-20">
        <SectionHeading
          kicker="The pipeline"
          title="Six specialists, one trip"
          lede="A fixed orchestration runs your request through six steps. Deterministic code decides; the language model only writes stories."
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {STEPS.map((step) => (
            <motion.div key={step.n} {...fadeUp}>
              <Card className="h-full p-5 sm:p-6">
                <p className="font-mono text-sm text-accent">{step.n}</p>
                <h3 className="mt-1 font-display text-lg font-semibold text-starlight">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-stardim">{step.body}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── What you get ─────────────────────────────────── */}
      <section className="pt-20">
        <SectionHeading
          kicker="Output"
          title="A decision package, not an event list"
        />
        <div className="grid gap-4 sm:grid-cols-2">
          {DELIVERABLES.map((d) => (
            <motion.div key={d.title} {...fadeUp}>
              <Card className="h-full p-5 sm:p-6">
                <h3 className="font-display text-base font-semibold text-accent">{d.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-stardim">{d.body}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Sites ────────────────────────────────────────── */}
      <section className="pt-20">
        <SectionHeading
          kicker="Field guide"
          title="Dark skies across India"
          lede="From Bortle 1 Himalayan plateaus to weeknight escapes near Bangalore."
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {SITES.map((site, i) => (
            <motion.div
              key={site.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.45, delay: (i % 3) * 0.08 }}
            >
              <div className="flex items-center justify-between rounded-xl border border-space-600/60 bg-space-900/70 px-4 py-3.5">
                <span className="font-display text-sm font-semibold text-starlight">{site.name}</span>
                <span className="text-xs text-starfaint">{site.meta}</span>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── Trust + CTA ──────────────────────────────────── */}
      <section className="pt-20">
        <motion.div {...fadeUp}>
          <Card className="relative overflow-hidden px-6 py-12 text-center sm:px-12">
            <div className="absolute inset-0 opacity-60">
              <Starfield density={0.8} />
            </div>
            <div className="relative">
              <h2 className="mx-auto max-w-xl font-display text-2xl font-bold text-starlight sm:text-3xl">
                Honest about uncertainty. Serious about backup plans.
              </h2>
              <p className="mx-auto mt-3 max-w-lg text-sm text-stardim sm:text-base">
                No forecast beyond its coverage. No dark site that blocks your target.
                No trip without a fallback.
              </p>
              <div className="mt-7">
                <Link to="/plan">
                  <Button>Start planning</Button>
                </Link>
              </div>
            </div>
          </Card>
        </motion.div>
      </section>
    </div>
  );
}
