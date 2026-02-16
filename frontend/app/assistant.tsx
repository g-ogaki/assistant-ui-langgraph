"use client";

import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import { DefaultChatTransport, UIMessage } from "ai";
import { useCreateThreadApiThreadsPost, getGetThreadsApiThreadsGetQueryKey } from "@/lib/api/default/default";
import { useQueryClient } from "@tanstack/react-query";

export function Assistant({ threadId, messages }: { threadId?: string, messages?: UIMessage[] }) {
  const { mutateAsync: createThread } = useCreateThreadApiThreadsPost();
  const queryClient = useQueryClient();

  const runtime = useChatRuntime({
    transport: new DefaultChatTransport({
      fetch: async (_, options) => {
        // redirect in new conversation invocation
        let currentThreadId = threadId;
        if (!currentThreadId) {
          const bodyData = JSON.parse(options?.body as string);
          await createThread({ data: { query: bodyData.query } }, {
            onSuccess: (response) => {
              if (response.status !== 200) {
                throw new Error('Failed to create thread');
              }
              currentThreadId = response.data.thread_id;
              window.history.replaceState(null, '', `/thread/${currentThreadId}`);
              queryClient.invalidateQueries({
                queryKey: getGetThreadsApiThreadsGetQueryKey(),
              });
            }
          });
        }

        const url = `/api/threads/${currentThreadId}/messages`;
        const response = await fetch(url, options);
        return response;
      },
      prepareSendMessagesRequest: async ({ messages }) => {
        const lastMessage = messages[messages.length - 1];
        return {
          body: {
            // @ts-ignore
            query: lastMessage.parts[0].text
          }
        };
      }
    }),
    messages,
    // TODO: support tool message
    // messages: [
    //   {
    //     id: 'msg-1',
    //     role: 'assistant',
    //     parts: [
    //       {
    //         // 1. Define the type (likely 'tool-invocation' or 'tool-call')
    //         type: 'tool-invocation',

    //         // 2. Helper properties required by the type
    //         toolCallId: 'call_001',
    //         toolName: 'weather_tool',

    //         // 3. Current state of the tool
    //         state: "output-available", // Indicates the tool has finished executing

    //         // 4. Flattened Input/Output (based on your error message)
    //         input: { city: 'New York' },
    //         output: { temperature: 72, condition: 'Sunny' }
    //       }
    //     ]
    //   }
    // ]
    adapters: { // Sucks: https://github.com/assistant-ui/assistant-ui/discussions/2900 
    }
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="h-dvh">
        <Thread />
      </div>
    </AssistantRuntimeProvider>
  );
};
