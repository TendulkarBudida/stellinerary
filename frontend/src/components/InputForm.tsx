import React, { useMemo, useState } from 'react';
import type { PlanRequest } from '../types';
import { Button, Card } from './ui';

interface InputFormProps {
  onSubmit: (request: PlanRequest) => void;
  isLoading: boolean;
}

const CITIES = [
  { name: 'Bangalore', lat: '12.9716', lon: '77.5946' },
  { name: 'Mysore', lat: '12.2958', lon: '76.6394' },
  { name: 'Chennai', lat: '13.0827', lon: '80.2707' },
  { name: 'Hyderabad', lat: '17.3850', lon: '78.4867' },
  { name: 'Pune', lat: '18.5204', lon: '73.8567' },
  { name: 'Mumbai', lat: '19.0760', lon: '72.8777' },
  { name: 'Delhi', lat: '28.6139', lon: '77.2090' },
  { name: 'Leh', lat: '34.1526', lon: '77.5771' },
];

const inputCls =
  'w-full rounded-lg border border-space-600 bg-space-950 px-3.5 py-2.5 text-base text-starlight placeholder:text-starfaint focus:border-accent focus:outline-none sm:text-sm';
const labelCls = 'mb-1.5 block font-display text-xs font-semibold uppercase tracking-wider text-stardim';

const STEP_TITLES = ['Where are you?', 'Which nights?', 'How do you observe?'];

const InputForm: React.FC<InputFormProps> = ({ onSubmit, isLoading }) => {
  const [step, setStep] = useState(0);
  const [city, setCity] = useState('Bangalore');
  const [lat, setLat] = useState('12.9716');
  const [lon, setLon] = useState('77.5946');
  const [dateStart, setDateStart] = useState(() => new Date().toISOString().split('T')[0]);
  const [dateEnd, setDateEnd] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 2);
    return d.toISOString().split('T')[0];
  });
  const [equipment, setEquipment] = useState<PlanRequest['equipment_level']>('naked_eye');
  const [maxTravelMinutes, setMaxTravelMinutes] = useState('180');
  const [primaryGoal, setPrimaryGoal] = useState('visual_observing');
  const [overnightAllowed, setOvernightAllowed] = useState(false);

  const nights = useMemo(() => {
    const ms = new Date(dateEnd).getTime() - new Date(dateStart).getTime();
    if (Number.isNaN(ms) || ms < 0) return 0;
    return Math.round(ms / 86400000) + 1;
  }, [dateStart, dateEnd]);

  const pickCity = (name: string, cLat: string, cLon: string) => {
    setCity(name);
    setLat(cLat);
    setLon(cLon);
  };

  const stepValid = step === 0 ? lat !== '' && lon !== '' : step === 1 ? nights >= 1 && nights <= 14 : true;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      user_lat: parseFloat(lat),
      user_lon: parseFloat(lon),
      user_city: city || undefined,
      date_start: dateStart,
      date_end: dateEnd,
      equipment_level: equipment,
      max_travel_minutes: maxTravelMinutes ? parseInt(maxTravelMinutes, 10) : undefined,
      primary_goal: primaryGoal,
      overnight_allowed: overnightAllowed,
    });
  };

  return (
    <Card className="mx-auto max-w-2xl p-5 sm:p-8">
      <div className="mb-6 flex items-center gap-2" aria-label="Form progress">
        {STEP_TITLES.map((title, i) => (
          <button
            key={title}
            type="button"
            onClick={() => i < step && setStep(i)}
            className="flex flex-1 flex-col gap-1.5"
            aria-current={i === step ? 'step' : undefined}
          >
            <span
              className={`h-1 rounded-full transition-colors ${
                i < step ? 'bg-accent' : i === step ? 'bg-accent/70' : 'bg-space-700'
              }`}
            />
            <span className={`text-left text-xs ${i === step ? 'text-accent' : 'text-starfaint'}`}>{title}</span>
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit}>
        {step === 0 && (
          <div>
            <h2 className="font-display text-xl font-semibold text-starlight">Where are you starting from?</h2>
            <p className="mt-1 text-sm text-stardim">Site distances and drive times are computed from this point.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {CITIES.map((c) => (
                <button
                  key={c.name}
                  type="button"
                  onClick={() => pickCity(c.name, c.lat, c.lon)}
                  className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
                    city === c.name
                      ? 'border-accent bg-accent/15 text-accent'
                      : 'border-space-600 text-stardim hover:border-accent/50 hover:text-starlight'
                  }`}
                >
                  {c.name}
                </button>
              ))}
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-3 [&>*]:min-w-0">
              <div>
                <label className={labelCls} htmlFor="city">City label</label>
                <input id="city" className={inputCls} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Bangalore" />
              </div>
              <div>
                <label className={labelCls} htmlFor="lat">Latitude</label>
                <input id="lat" className={inputCls} type="number" step="any" value={lat} onChange={(e) => setLat(e.target.value)} required />
              </div>
              <div>
                <label className={labelCls} htmlFor="lon">Longitude</label>
                <input id="lon" className={inputCls} type="number" step="any" value={lon} onChange={(e) => setLon(e.target.value)} required />
              </div>
            </div>
          </div>
        )}

        {step === 1 && (
          <div>
            <h2 className="font-display text-xl font-semibold text-starlight">Which nights can you go?</h2>
            <p className="mt-1 text-sm text-stardim">Up to 14 nights. Each night gets its own schedule and forecast check.</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 [&>*]:min-w-0">
              <div>
                <label className={labelCls} htmlFor="dateStart">First night</label>
                <input id="dateStart" className={inputCls} type="date" value={dateStart} onChange={(e) => setDateStart(e.target.value)} required />
              </div>
              <div>
                <label className={labelCls} htmlFor="dateEnd">Last night</label>
                <input id="dateEnd" className={inputCls} type="date" value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} required />
              </div>
            </div>
            <p className="mt-3 text-sm text-accent">
              {nights >= 1 && nights <= 14 ? `${nights} observing night${nights > 1 ? 's' : ''} will be planned.` : 'Pick an end date on or after the start date (max 14 nights).'}
            </p>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 className="font-display text-xl font-semibold text-starlight">How do you observe?</h2>
            <p className="mt-1 text-sm text-stardim">This tunes event ranking, the schedule, and your packing list.</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 [&>*]:min-w-0">
              <div>
                <label className={labelCls} htmlFor="equipment">Equipment</label>
                <select id="equipment" className={inputCls} value={equipment} onChange={(e) => setEquipment(e.target.value as PlanRequest['equipment_level'])}>
                  <option value="naked_eye">Naked eye</option>
                  <option value="binoculars">Binoculars</option>
                  <option value="telescope">Telescope</option>
                </select>
              </div>
              <div>
                <label className={labelCls} htmlFor="goal">Primary goal</label>
                <select id="goal" className={inputCls} value={primaryGoal} onChange={(e) => setPrimaryGoal(e.target.value)}>
                  <option value="visual_observing">Visual observing</option>
                  <option value="meteor_shower">Meteor shower</option>
                  <option value="planets">Planets</option>
                  <option value="milky_way">Milky Way</option>
                  <option value="deep_sky">Deep sky</option>
                  <option value="astrophotography">Astrophotography</option>
                </select>
              </div>
              <div>
                <label className={labelCls} htmlFor="travel">Max drive (minutes)</label>
                <input id="travel" className={inputCls} type="number" min="15" value={maxTravelMinutes} onChange={(e) => setMaxTravelMinutes(e.target.value)} />
              </div>
              <div className="flex items-end pb-1">
                <label className="flex cursor-pointer items-center gap-2.5 text-sm text-stardim">
                  <input
                    type="checkbox"
                    checked={overnightAllowed}
                    onChange={(e) => setOvernightAllowed(e.target.checked)}
                    className="h-4 w-4 accent-[#67e8f9]"
                  />
                  Allow overnight / long-distance trips
                </label>
              </div>
            </div>
          </div>
        )}

        <div className="mt-7 flex items-center justify-between gap-3">
          <div>
            {step > 0 && (
              <Button type="button" variant="ghost" onClick={() => setStep(step - 1)}>
                ← Back
              </Button>
            )}
          </div>
          {step < 2 ? (
            <Button type="button" disabled={!stepValid} onClick={() => setStep(step + 1)}>
              Continue →
            </Button>
          ) : (
            <Button type="submit" disabled={isLoading || !stepValid}>
              {isLoading ? 'Charting your sky…' : 'Generate expedition'}
            </Button>
          )}
        </div>
      </form>
    </Card>
  );
};

export default InputForm;
