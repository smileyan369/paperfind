import { HashRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import HomePage from './pages/HomePage';
import KeywordsPage from './pages/KeywordsPage';
import SettingsPage from './pages/SettingsPage';
import ErrorBoundary from './components/common/ErrorBoundary';
import { CrawlProvider } from './contexts/CrawlContext';
import { ConfigProvider } from './contexts/ConfigContext';
import WelcomeModal from './components/common/WelcomeModal';

export default function App() {
  return (
    <ErrorBoundary>
      <WelcomeModal />
      <ConfigProvider>
        <CrawlProvider>
          <HashRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route path="/" element={<HomePage />} />
                <Route path="/keywords" element={<KeywordsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Routes>
          </HashRouter>
        </CrawlProvider>
      </ConfigProvider>
    </ErrorBoundary>
  );
}
