"use client";

import { useChatStore } from "@/lib/store";
import { Assistant } from "./assistant";

export default function Home() {
  const remountKey = useChatStore((state) => state.remountKey);
  return <Assistant key={remountKey} />;
}
