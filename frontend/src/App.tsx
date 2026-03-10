import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import QueryChat from './pages/QueryChat'
import QueryList from './pages/QueryList'
import DashboardList from './pages/DashboardList'
import DashboardBuilder from './pages/DashboardBuilder'
import DashboardView from './pages/DashboardView'
import DashboardVisionamos from './pages/DashboardVisionamos'
import DataExplorer from './pages/DataExplorer'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/consultas" element={<QueryList />} />
        <Route path="/consultas/nueva" element={<QueryChat />} />
        <Route path="/tableros" element={<DashboardList />} />
        <Route path="/tableros/nuevo" element={<DashboardBuilder />} />
        <Route path="/tableros/visionamos" element={<DashboardVisionamos />} />
        <Route path="/tableros/saved/:id" element={<DashboardView />} />
        <Route path="/datos" element={<DataExplorer />} />
      </Route>
    </Routes>
  )
}
