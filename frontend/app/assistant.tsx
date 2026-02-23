"use client";

import { AssistantRuntimeProvider, AttachmentAdapter } from "@assistant-ui/react";
import { useChatRuntime } from "@assistant-ui/react-ai-sdk";
import { Thread } from "@/components/assistant-ui/thread";
import { DefaultChatTransport, UIMessage } from "ai";
import { useCreateThreadApiThreadsPost, getGetThreadsApiThreadsGetQueryKey } from "@/lib/api/default/default";
import { useQueryClient } from "@tanstack/react-query";

const vercelAttachmentAdapter: AttachmentAdapter = {
  accept: "image/*",
  add: async ({ file }) => {
    return {
      id: Math.random().toString(36).substring(7),
      type: "image",
      name: file.name,
      file,
      contentType: file.type,
      status: { type: "requires-action", reason: "composer-send" },
    };
  },
  async send(attachment) {
    const reader = new FileReader();
    const dataUrl = await new Promise<string>((resolve, reject) => {
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(attachment.file);
    });
    return {
      ...attachment,
      status: { type: "complete" },
      content: [{ type: "image", image: dataUrl }],
    };
  },
  async remove() { },
};

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
        const parts = lastMessage.parts.map((part) => {
          if (part.type === "text") {
            return { type: "text", text: part.text };
          }
          if ((part.type as any) === "image") {
            console.log("image", part);
            return {
              type: "image_url",
              image_url: { url: (part as any).image },
            };
          }
          return null;
        }).filter(Boolean);

        return {
          body: {
            query: parts.length === 1 && parts[0]!.type === "text" ? (parts[0]! as any).text : parts,
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
      attachments: vercelAttachmentAdapter,
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
