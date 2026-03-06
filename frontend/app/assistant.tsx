"use client";

import { AssistantRuntimeProvider, AttachmentAdapter } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import { DefaultChatTransport, UIMessage } from "ai";
import { useCreateThreadApiThreadsPost, getGetThreadsApiThreadsGetQueryKey, useUpdateThreadApiThreadsThreadIdPut } from "@/lib/api/default/default";
import { useQueryClient } from "@tanstack/react-query";

export function Assistant({ threadId, messages }: { threadId?: string, messages?: UIMessage[] }) {
  const { mutateAsync: createThread } = useCreateThreadApiThreadsPost();
  const { mutateAsync: updateThread } = useUpdateThreadApiThreadsThreadIdPut();
  const queryClient = useQueryClient();

  const runtime = useChatRuntime({
    transport: new DefaultChatTransport({
      fetch: async (_, options) => {
        let currentThreadId = threadId;
        if (currentThreadId) {
          // update thread's updated_at
          await updateThread({ threadId: currentThreadId });
        } else {
          // redirect in new conversation invocation
          const bodyData = JSON.parse(options?.body as string);
          await createThread({ data: { query: bodyData.query } }, {
            onSuccess: (response) => {
              if (response.status !== 200) {
                throw new Error('Failed to create thread');
              }
              currentThreadId = response.data.thread_id;
              window.history.replaceState(null, '', `/thread/${currentThreadId}`);
            }
          });
        }

        const url = `/api/threads/${currentThreadId}/messages`;
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
