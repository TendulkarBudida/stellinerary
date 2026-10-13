import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { ExpeditionPlan } from '../types';
import { fetchPlanById, fetchPlans, loadTripIds, refreshPlan, removeTripId } from '../api';
import type { PlanSummary } from '../api';
import Highlights from '../components/Highlights';
import PlanOptions from '../components/PlanOptions';
import NightPlans from '../components/NightPlans';
import GearStory from '../components/GearStory';
import { Button, Card, EmptyState, SectionHeading } from '../components/ui';

export default function Trips() {
  const [summaries, setSummaries] = useState<PlanSummary[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);
  const [openPlan, setOpenPlan] = useState<ExpeditionPlan | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const server = await fetchPlans();
      const localIds = loadTripIds();
      const merged = new Map<string, PlanSummary>();
      for (const s of server) merged.set(s.plan_id, s);
      for (const id of localIds) {
        if (!merged.has(id)) merged.set(id, { plan_id: id });
      }
      setSummaries([...merged.values()]);
    } catch (err: unknown) {
      const localIds = loadTripIds();
      if (localIds.length > 0) {
        setSummaries(localIds.map((plan_id) => ({ plan_id })));
      } else {
        setError(err instanceof Error ? err.message : 'Could not load trips.');
      }
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const server = await fetchPlans();
        if (!alive) return;
        const localIds = loadTripIds();
        const merged = new Map<string, PlanSummary>();
        for (const s of server) merged.set(s.plan_id, s);
        for (const id of localIds) {
          if (!merged.has(id)) merged.set(id, { plan_id: id });
        }
        setSummaries([...merged.values()]);
      } catch (err: unknown) {
        if (!alive) return;
        const localIds = loadTripIds();
        if (localIds.length > 0) {
          setSummaries(localIds.map((plan_id) => ({ plan_id })));
        } else {
          setError(err instanceof Error ? err.message : 'Could not load trips.');
        }
      } finally {
        if (alive) setLoadingList(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const openTrip = async (planId: string) => {
    setOpenId(planId);
    setOpenPlan(null);
    setLoadingPlan(true);
    setError(null);
    try {
      setOpenPlan(await fetchPlanById(planId));
      window.scrollTo({ top: 0 });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not open trip.');
    } finally {
      setLoadingPlan(false);
    }
  };

  const handleRefresh = async () => {
    if (!openId) return;
    setRefreshing(true);
    try {
      const updated = await refreshPlan(openId);
      setOpenPlan(updated);
      void loadList();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Refresh failed.');
    } finally {
      setRefreshing(false);
    }
  };

  const handleRemove = (planId: string) => {
    const remaining = removeTripId(planId);
    setSummaries((prev) => prev.filter((s) => remaining.includes(s.plan_id)));
    if (openId === planId) {
      setOpenId(null);
      setOpenPlan(null);
    }
  };

  if (openPlan) {
    return (
      <div className="space-y-4 pt-6">
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="ghost" onClick={() => { setOpenId(null); setOpenPlan(null); }}>
            ← All trips
          </Button>
          <Button variant="ghost" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? 'Refreshing…' : '↻ Refresh with live weather'}
          </Button>
        </div>
        {openPlan.contingency_note && (
          <div className="rounded-xl border border-warn/40 bg-warn/10 p-4 text-sm text-warn" role="status">
            {openPlan.contingency_note}
          </div>
        )}
        <Highlights events={openPlan.ranked_events} />
        {openPlan.options.length > 0 ? (
          <PlanOptions options={openPlan.options} rankedSites={openPlan.ranked_sites} stories={openPlan.stories} />
        ) : openPlan.chosen_site && openPlan.gear ? (
          <>
            <NightPlans site={openPlan.chosen_site} nights={openPlan.night_plans} />
            <GearStory gear={openPlan.gear} stories={openPlan.stories} />
          </>
        ) : null}
      </div>
    );
  }

  return (
    <div className="pt-10">
      <SectionHeading
        kicker="Saved"
        title="My trips"
        lede="Every generated expedition is kept. Reopen it, or refresh it against live weather before you leave."
      />
      {error && (
        <div className="mx-auto mb-4 max-w-2xl rounded-xl border border-danger/40 bg-danger/10 p-4 text-sm text-danger" role="alert">
          {error}
        </div>
      )}
      {loadingList || loadingPlan ? (
        <p className="text-center text-sm text-stardim">Loading trips…</p>
      ) : summaries.length === 0 ? (
        <div className="mx-auto max-w-2xl">
          <EmptyState
            title="No trips yet"
            body="Generate your first expedition and it will appear here automatically."
          />
          <div className="mt-4 text-center">
            <Link to="/plan" className="font-display text-sm font-semibold text-accent hover:underline">
              Plan an expedition →
            </Link>
          </div>
        </div>
      ) : (
        <div className="mx-auto grid max-w-3xl gap-3">
          {summaries.map((trip) => (
            <Card key={trip.plan_id} className="flex flex-wrap items-center justify-between gap-3 p-4 sm:px-5">
              <div>
                <p className="font-display text-sm font-semibold text-starlight">
                  {trip.site_name ?? 'Expedition'}
                  {trip.date_start && (
                    <span className="ml-2 font-body text-xs font-normal text-starfaint">
                      {new Date(trip.date_start).toLocaleDateString()}
                    </span>
                  )}
                </p>
                <p className="mt-0.5 font-mono text-xs text-starfaint">
                  {trip.plan_id.slice(0, 8)}
                  {trip.updated_at && ` · updated ${new Date(trip.updated_at).toLocaleString()}`}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => void openTrip(trip.plan_id)}>
                  Open
                </Button>
                <Button variant="danger-ghost" onClick={() => handleRemove(trip.plan_id)}>
                  Forget
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
