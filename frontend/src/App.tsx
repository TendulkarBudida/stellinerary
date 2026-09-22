import { useState } from 'react';
import type { PlanRequest, ExpeditionPlan } from './types';
import { fetchPlan } from './api';
import InputForm from './components/InputForm';
import Highlights from './components/Highlights';
import SiteSchedule from './components/SiteSchedule';
import GearStory from './components/GearStory';
import './App.css';

function App() {
  const [plan, setPlan] = useState<ExpeditionPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGeneratePlan = async (request: PlanRequest) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPlan(request);
      setPlan(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to generate plan.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setPlan(null);
  };

  return (
    <div className="App">
      <header className="header">
        <h1>Stellinerary</h1>
        <p className="subtitle">Night Sky Expedition Orchestrator</p>
      </header>

      <main>
        {error && (
          <div className="error-card">
            <p>Error: {error}</p>
          </div>
        )}

        {!plan ? (
          <InputForm onSubmit={handleGeneratePlan} isLoading={loading} />
        ) : (
          <div className="dashboard">
            <div className="dashboard-header">
              <button onClick={handleReset} className="btn-secondary">← New Plan</button>
              <span>Generated at: {new Date(plan.generated_at).toLocaleString()}</span>
            </div>
            
            <Highlights events={plan.ranked_events} />
            <SiteSchedule site={plan.chosen_site} weather={plan.weather_forecast} schedule={plan.schedule} />
            <GearStory gear={plan.gear} stories={plan.stories} />
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
