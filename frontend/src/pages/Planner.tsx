import { useState } from 'react';
import { motion } from 'motion/react';
import type { ExpeditionPlan, PlanRequest } from '../types';
import { fetchPlan, saveTripId } from '../api';
import InputForm from '../components/InputForm';
import LoadingJourney from '../components/LoadingJourney';
import Highlights from '../components/Highlights';
import PlanOptions from '../components/PlanOptions';
import NightPlans from '../components/NightPlans';
import GearStory from '../components/GearStory';
import Starfield from '../components/Starfield';
import { Badge, Button, Card } from '../components/ui';

export default function Planner() {
  const [plan, setPlan] = useState<ExpeditionPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (request: PlanRequest) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPlan(request);
      if (data.plan_id) saveTripId(data.plan_id);
      setPlan(data);
      window.scrollTo({ top: 0 });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to generate plan.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="pt-10">
        <LoadingJourney />
      </div>
    );
  }

  if (!plan) {
    return (
      <div className="pt-10">
        <div className="mx-auto mb-8 max-w-2xl text-center">
          <h1 className="font-display text-3xl font-bold text-starlight sm:text-4xl">Chart a new expedition</h1>
          <p className="mt-2 text-stardim">Three quick steps. About a minute of computation. A full trip package.</p>
        </div>
        {error && (
          <div className="mx-auto mb-4 max-w-2xl rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger" role="alert">
            {error}
          </div>
        )}
        <InputForm onSubmit={handleGenerate} isLoading={loading} />
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }} className="space-y-4 pt-6">
      <Card className="relative overflow-hidden">
        <div className="absolute inset-0 opacity-70">
          <Starfield density={0.6} />
        </div>
        <div className="relative flex flex-wrap items-center justify-between gap-3 p-5 sm:p-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Expedition ready</p>
            <h1 className="mt-1 font-display text-2xl font-bold text-starlight sm:text-3xl">
              {plan.chosen_site ? `${plan.chosen_site.name}` : 'Your night sky plan'}
            </h1>
            <p className="mt-1 text-sm text-stardim">
              {new Date(plan.request.date_start).toLocaleDateString()} → {new Date(plan.request.date_end).toLocaleDateString()}
              {' · '}Generated {new Date(plan.generated_at).toLocaleString()}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {plan.plan_id && <Badge tone="neutral">Trip {plan.plan_id.slice(0, 8)}</Badge>}
            <Button variant="ghost" onClick={() => { setPlan(null); setError(null); }}>
              ← New plan
            </Button>
          </div>
        </div>
      </Card>

      {plan.contingency_note && (
        <div className="break-words rounded-xl border border-warn/40 bg-warn/10 p-4 text-sm text-warn" role="status">
          {plan.contingency_note}
        </div>
      )}

      <Highlights events={plan.ranked_events} />
      {plan.options.length > 0 ? (
        <PlanOptions options={plan.options} rankedSites={plan.ranked_sites} stories={plan.stories} />
      ) : plan.chosen_site && plan.gear ? (
        <>
          <NightPlans site={plan.chosen_site} nights={plan.night_plans} />
          <GearStory gear={plan.gear} stories={plan.stories} />
        </>
      ) : null}
    </motion.div>
  );
}
