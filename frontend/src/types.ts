export interface PlanRequest {
    user_lat: number;
    user_lon: number;
    user_city?: string;
    date_start: string;
    date_end: string;
    equipment_level: 'naked_eye' | 'binoculars' | 'telescope' | 'solar_filter';
}

export interface CelestialEvent {
    id: string;
    name: string;
    type: string;
    peak_date: string;
    active_start: string;
    active_end: string;
    description: string;
    zhr?: number;
    equipment: string;
    viewing_direction?: string;
    best_hours?: string;
}

export interface Site {
    id: string;
    name: string;
    state: string;
    lat: number;
    lon: number;
    altitude_m: number;
    bortle_class: number;
}

export interface RankedSite {
    site: Site;
    distance_km: number;
    overall_score: number;
    ranking_reason: string;
}

export interface HourlyWeather {
    datetime_utc: string;
    cloud_cover_pct: number;
    temperature_c?: number;
}

export interface SiteWeatherForecast {
    summary: string;
    hourly: HourlyWeather[];
}

export interface ScheduleEntry {
    time_local: string;
    end_time_local?: string;
    title: string;
    description: string;
    direction?: string;
    altitude_deg?: number;
    is_weather_dependent: boolean;
    dark_adaptation_note?: string;
}

export interface ObservationSchedule {
    entries: ScheduleEntry[];
    astronomical_twilight_end?: string;
    astronomical_twilight_start?: string;
    moon_rise?: string;
    moon_set?: string;
    moon_phase_pct?: number;
}

export interface GearItem {
    name: string;
    category: string;
    reason: string;
}

export interface GearList {
    items: GearItem[];
    warnings: string[];
}

export interface ObjectStory {
    event_id: string;
    title: string;
    story_text: string;
}

export interface ExpeditionPlan {
    request: PlanRequest;
    ranked_events: CelestialEvent[];
    ranked_sites: RankedSite[];
    chosen_site: Site;
    weather_forecast: SiteWeatherForecast;
    schedule: ObservationSchedule;
    gear: GearList;
    stories: ObjectStory[];
    generated_at: string;
}
