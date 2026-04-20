"use client";

import DashboardLayout from "@/components/DashboardLayout";
import ActivityFeed from "@/components/activities/ActivityFeed";

export default function ActivitiesPage() {
  return (
    <DashboardLayout>
      <ActivityFeed mode="page" limit={100} />
    </DashboardLayout>
  );
}
