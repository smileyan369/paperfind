import { Outlet } from 'react-router-dom';
import Header from './Header';

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <footer className="text-center py-4 text-xs text-slate-400 border-t border-white/60 bg-white/55 backdrop-blur">
        by: 星海无言  
      </footer>
    </div>
  );
}
