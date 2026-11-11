import AppLayout from "./components/layout/AppLayout.jsx";

export default function App() {
  return (
    <AppLayout>
      <main className="mx-auto flex min-h-[70vh] max-w-3xl flex-col items-center justify-center px-6 text-center">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-indigo-600">
          Credential Lifecycle Management
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900">
          Frontend is running
        </h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-slate-600">
          The application foundation is ready. Product features will be added in
          future development phases.
        </p>
      </main>
    </AppLayout>
  );
}
