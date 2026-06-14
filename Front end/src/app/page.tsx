import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 p-6 text-center dark:bg-gray-950">
      <div className="max-w-md space-y-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-950 dark:text-gray-55">
            GradeMIND
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Establish the complete AI-powered grading and educational analytics foundation.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row justify-center">
          <Link
            href="/login"
            className="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-6 font-semibold text-white transition-colors hover:bg-blue-700 active:bg-blue-800"
          >
            Access Login
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-gray-300 bg-white px-6 font-semibold text-gray-700 transition-colors hover:bg-gray-50 active:bg-gray-100 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-850"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
