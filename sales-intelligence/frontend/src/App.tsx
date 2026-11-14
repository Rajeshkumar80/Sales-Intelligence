import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Analytics from './pages/Analytics'
import Transactions from './pages/Transactions'
import Ingestion from './pages/Ingestion'
import Jobs from './pages/Jobs'
import HiveAnalytics from './pages/HiveAnalytics'
import Reports from './pages/Reports'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/transactions" element={<Transactions />} />
        <Route path="/ingestion" element={<Ingestion />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/hive" element={<HiveAnalytics />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Overview />} />
      </Route>
    </Routes>
  )
}
