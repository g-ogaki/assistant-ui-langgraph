"use client";

import { useChatStore } from "@/lib/store";
import { Assistant } from "./assistant";
import { useThreadId } from "./providers";

export default function Home() {
  const remountKey = useChatStore((state) => state.remountKey);
  const threadIdRef = useThreadId();
  threadIdRef.current = null;
  return <Assistant key={remountKey} />;
}
