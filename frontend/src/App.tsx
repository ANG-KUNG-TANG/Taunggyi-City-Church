
import { Church, Users, ShieldCheck } from 'lucide-react'

function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-12">
      <section className="w-full max-w-3xl rounded-2xl border border-slate-200 bg-white p-8 shadow-sm sm:p-12">
        <div className="mb-8 flex h-14 w-14 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
          <Church size={30} />
        </div>

        <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-indigo-700">
          Taunggyi City Church
        </p>

        <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Community Management System
        </h1>

        <p className="mt-4 max-w-xl leading-7 text-slate-600">
          A centralised platform for managing church members, zones,
          attendance, activities, announcements, and administrative
          operations.
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-200 p-5">
            <Users className="mb-3 text-indigo-700" size={25} />
            <h2 className="font-semibold text-slate-900">
              Community Management
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Organised member and zone management.
            </p>
          </div>

          <div className="rounded-xl border border-slate-200 p-5">
            <ShieldCheck className="mb-3 text-indigo-700" size={25} />
            <h2 className="font-semibold text-slate-900">
              Secure Access
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Role-based access for authorised church personnel.
            </p>
          </div>
        </div>

        <div className="mt-10 border-t border-slate-200 pt-6">
          <p className="text-xs text-slate-500">
            Taunggyi City Church · Community Management System
          </p>
        </div>
      </section>
    </main>
  )
}

export default App
