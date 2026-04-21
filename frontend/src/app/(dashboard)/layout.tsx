import Navigation from "@/components/Navigation";
import { AIAssistant } from "@/components/AIAssistant";

export default function DashboardGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-900">
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
      <AIAssistant />
    </div>
  );
}
