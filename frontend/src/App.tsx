import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Cover from './pages/Cover';
import Dashboard from './pages/Dashboard';
import Transactions, { TransactionDetail } from './pages/Transactions';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Cover />} />
        <Route path="/dashboard" element={<Layout />}>
          <Route index element={<Dashboard />} />
        </Route>
        <Route path="/transactions" element={<Layout />}>
          <Route index element={<Transactions />} />
          <Route path=":transactionId" element={<TransactionDetail />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
