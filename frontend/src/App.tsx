import { Route, Routes } from 'react-router-dom';
import SiteShell from './components/SiteShell';
import RequireAuth from './components/RequireAuth';
import Landing from './pages/Landing';
import Planner from './pages/Planner';
import Trips from './pages/Trips';

function App() {
  return (
    <Routes>
      <Route element={<SiteShell />}>
        <Route index element={<Landing />} />
        <Route path="plan" element={<RequireAuth><Planner /></RequireAuth>} />
        <Route path="trips" element={<RequireAuth><Trips /></RequireAuth>} />
        <Route path="*" element={<Landing />} />
      </Route>
    </Routes>
  );
}

export default App;
