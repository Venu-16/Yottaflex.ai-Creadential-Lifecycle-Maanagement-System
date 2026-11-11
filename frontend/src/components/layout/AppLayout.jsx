export default function AppLayout({ children }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <span className="font-semibold text-slate-800">Credential Platform</span>
        </div>
      </header>
      {children}
    </div>
  );
}
