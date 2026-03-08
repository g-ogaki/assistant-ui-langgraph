"use client";

import { Assistant } from "@/app/assistant";
import { useParams } from "next/navigation";
import { useGetMessagesApiThreadsThreadIdMessagesGet } from "@/lib/api/default/default";
import { Message } from "@/lib/api/model";
import { UIMessage } from "ai";
import { useThreadId } from "@/app/providers";

function convertMessage(messages: Message[]): UIMessage[] {
  return messages.map(message => ({
    id: message.id!,
    role: message.type === "human" ? "user" : "assistant",
    parts: message.type === "tool" ? [{
      type: `tool-${message.name}`,
      toolCallId: message.tool_call_id!,
      state: "output-available",
      input: message.args,
      output: message.output,
    }] : [{
      type: "text",
      text: message.content
    }]
  }))
}

export default function Home() {
  const { threadId: threadIdParams } = useParams();
  const threadId = threadIdParams as string;
  const threadIdRef = useThreadId();
  threadIdRef.current = threadId;
  const { data, isLoading } = useGetMessagesApiThreadsThreadIdMessagesGet(threadId);

  if (isLoading) {
    return <div>Loading...</div>
  }

  return (
    <Assistant
      messages={convertMessage(data?.status === 200 ? data.data.messages : [])}
    />
  );
}