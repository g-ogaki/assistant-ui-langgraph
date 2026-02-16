"use client";

import { Assistant } from "@/app/assistant";
import { useParams } from "next/navigation";
import { useGetMessagesApiThreadsThreadIdMessagesGet } from "@/lib/api/default/default";
import { Message } from "@/lib/api/model";
import { UIMessage } from "ai";

function convertMessage(messages: Message[]): UIMessage[] {
  return messages.map(message => ({
    id: message.id!,
    role: message.type === "human" ? "user" : "assistant",
    parts: [{ type: "text", text: message.content }]
  }))
}

export default function Home() {
  const { threadId } = useParams();
  const { data, isLoading } = useGetMessagesApiThreadsThreadIdMessagesGet(threadId as string);

  if (isLoading) {
    return <div>Loading...</div>
  }

  return (
    <Assistant
      threadId={threadId as string}
      messages={convertMessage(data?.status === 200 ? data?.data?.messages : [])}
    />
  );
}