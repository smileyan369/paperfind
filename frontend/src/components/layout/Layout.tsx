import { Outlet } from 'react-router-dom';
import Header from './Header';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="text-center py-4 text-xs text-gray-400 border-t border-gray-200 bg-white">
        From：星海无言
      </footer>
    </div>
  );
}
