/**
 * Live Command Center — /dashboard/ideas/[id]/live
 *
 * Server Component by design: metadata, params resolution, and the page
 * shell render on the server. The WebSocket connection and all live UI
 * state live exclusively inside <CommandCenter /> (Client Component).
 */

import type { Metadata } from "next";
import { CommandCenter } from "@/components/command-center/CommandCenter";

export const metadata: Metadata = {
  title: "Live Incubation | AI Venture OS",
  description: "Real-time agent execution stream.",
};

export default async function LiveIncubationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <CommandCenter ideaId={id} />;
}
