"use client";

import ActivityFeed from "@/components/activities/ActivityFeed";

export default function ActivitiesPage() {
  return <ActivityFeed mode="page" limit={100} />;
}
