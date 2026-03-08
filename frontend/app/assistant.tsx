"use client";

import { AssistantRuntimeProvider } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import { DefaultChatTransport, UIMessage } from "ai";
import { useCreateThreadApiThreadsPost, getGetThreadsApiThreadsGetQueryKey, useUpdateThreadApiThreadsThreadIdPut } from "@/lib/api/default/default";
import { useQueryClient } from "@tanstack/react-query";
import { useThreadId } from "@/app/providers";

export function Assistant({ messages }: { messages?: UIMessage[] }) {
  const { mutateAsync: createThread } = useCreateThreadApiThreadsPost();
  const { mutateAsync: updateThread } = useUpdateThreadApiThreadsThreadIdPut();
  const queryClient = useQueryClient();
  const threadIdRef = useThreadId();

  const runtime = useChatRuntime({
    transport: new DefaultChatTransport({
      fetch: async (_, options) => {
        if (threadIdRef.current) {
          // update thread's updated_at
          await updateThread({ threadId: threadIdRef.current });
        } else {
          // redirect in new conversation invocation
          const bodyData = JSON.parse(options?.body as string);
          await createThread({ data: { query: bodyData.query } }, {
            onSuccess: (response) => {
              if (response.status !== 200) {
                throw new Error('Failed to create thread');
              }
              threadIdRef.current = response.data.thread_id;
              window.history.pushState(null, '', `/thread/${threadIdRef.current}`);
            }
          });
        }

        const url = `/api/threads/${threadIdRef.current}/messages`;
        const response = await fetch(url, options);
        queryClient.invalidateQueries({
          queryKey: getGetThreadsApiThreadsGetQueryKey(),
        });
        return response;
      },
      prepareSendMessagesRequest: async ({ messages }) => {
        const lastMessage = messages[messages.length - 1];
        const part = lastMessage.parts[0]
        return {
          body: {
            query: part.type === 'text' ? part.text : '',
          }
        };
      }
    }),
    messages,
    adapters: { // Sucks: https://github.com/assistant-ui/assistant-ui/discussions/2900
      history: undefined,
      threadList: undefined,
      attachments: undefined,
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
