import React, { useState } from 'react';
import type { PlanRequest } from '../types';

interface InputFormProps {
    onSubmit: (request: PlanRequest) => void;
    isLoading: boolean;
}

const InputForm: React.FC<InputFormProps> = ({ onSubmit, isLoading }) => {
    const [lat, setLat] = useState('12.9716'); // Default to Bangalore
    const [lon, setLon] = useState('77.5946');
    const [city, setCity] = useState('Bangalore');
    const [dateStart, setDateStart] = useState(() => {
        const d = new Date();
        return d.toISOString().split('T')[0];
    });
    const [dateEnd, setDateEnd] = useState(() => {
        const d = new Date();
        d.setDate(d.getDate() + 3);
        return d.toISOString().split('T')[0];
    });
    const [equipment, setEquipment] = useState<PlanRequest['equipment_level']>('naked_eye');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onSubmit({
            user_lat: parseFloat(lat),
            user_lon: parseFloat(lon),
            user_city: city,
            date_start: dateStart,
            date_end: dateEnd,
            equipment_level: equipment,
        });
    };

    return (
        <div className="card input-form">
            <h2>Plan Your Stargazing Expedition</h2>
            <form onSubmit={handleSubmit}>
                <div className="form-group row">
                    <div className="col">
                        <label>City (Optional)</label>
                        <input type="text" value={city} onChange={(e) => setCity(e.target.value)} />
                    </div>
                </div>
                <div className="form-group row">
                    <div className="col">
                        <label>Latitude</label>
                        <input type="number" step="any" value={lat} onChange={(e) => setLat(e.target.value)} required />
                    </div>
                    <div className="col">
                        <label>Longitude</label>
                        <input type="number" step="any" value={lon} onChange={(e) => setLon(e.target.value)} required />
                    </div>
                </div>
                <div className="form-group row">
                    <div className="col">
                        <label>Start Date</label>
                        <input type="date" value={dateStart} onChange={(e) => setDateStart(e.target.value)} required />
                    </div>
                    <div className="col">
                        <label>End Date</label>
                        <input type="date" value={dateEnd} onChange={(e) => setDateEnd(e.target.value)} required />
                    </div>
                </div>
                <div className="form-group">
                    <label>Equipment</label>
                    <select value={equipment} onChange={(e) => setEquipment(e.target.value as any)}>
                        <option value="naked_eye">Naked Eye (No equipment)</option>
                        <option value="binoculars">Binoculars</option>
                        <option value="telescope">Telescope</option>
                    </select>
                </div>
                <button type="submit" disabled={isLoading} className="btn-primary">
                    {isLoading ? 'Orchestrating Plan...' : 'Generate Plan'}
                </button>
            </form>
        </div>
    );
};

export default InputForm;
