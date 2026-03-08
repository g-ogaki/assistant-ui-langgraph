"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  useGetThreadsApiThreadsGet,
  getGetThreadsApiThreadsGetQueryKey,
  useDeleteThreadApiThreadsThreadIdDelete,
} from "@/lib/api/default/default";
import {
  PlusIcon,
  MessageSquareIcon,
  ChevronLeftIcon,
  Trash2Icon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useChatStore } from "@/lib/store";

export function Sidebar() {
  const { threadId } = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isCollapsed, setIsCollapsed] = useState(true);
  const newChat = useChatStore((state) => state.newChat);

  const { data } = useGetThreadsApiThreadsGet();
  const { mutate: deleteThread } = useDeleteThreadApiThreadsThreadIdDelete({
    mutation: {
      onMutate: async (variables) => {
        const queryKey = getGetThreadsApiThreadsGetQueryKey();
        await queryClient.cancelQueries({ queryKey });

        const previousThreads = queryClient.getQueryData(queryKey);

        queryClient.setQueryData(queryKey, (old: any) => {
          if (!old || !old.data || !old.data.threads) return old;
          return {
            ...old,
            data: {
              ...old.data,
              threads: old.data.threads.filter(
                (t: any) => t.thread_id !== variables.threadId
              ),
            },
          };
        });

        // TODO: Thread deletion just after new chat invocation (threadId === undefined) should be routed to "/".
        if (threadId === variables.threadId) {
          router.push("/");
        }

        return { previousThreads };
      },
      onError: (err, variables, context) => {
        if (context?.previousThreads) {
          queryClient.setQueryData(
            getGetThreadsApiThreadsGetQueryKey(),
            context.previousThreads
          );
        }
      },
      onSettled: () => {
        queryClient.invalidateQueries({
          queryKey: getGetThreadsApiThreadsGetQueryKey(),
        });
      },
    },
  });

  const threadsData = data?.status === 200 ? data.data.threads : [];

  const handleDelete = useCallback(
    (e: React.MouseEvent, id: string) => {
      e.preventDefault();
      e.stopPropagation();
      deleteThread({ threadId: id });
    },
    [deleteThread]
  );

  const toggleCollapsed = useCallback(() => {
    setIsCollapsed((prev) => !prev);
  }, []);

  return (
    <div
      className={cn(
        "relative flex flex-col h-screen bg-zinc-900 border-r border-zinc-800 text-zinc-100 transition-all duration-300 ease-in-out shrink-0",
        isCollapsed ? "w-0 border-r-0" : "w-64"
      )}
    >
      <div className={cn("flex flex-col h-full w-64 p-4 overflow-hidden transition-opacity duration-300", isCollapsed ? "opacity-0 invisible" : "opacity-100 visible")}>
        <Button
          onClick={() => {
            newChat();
            router.push("/");
          }}
          className="mt-1 mb-6 flex items-center justify-start gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-zinc-700 w-full"
        >
          <PlusIcon size={18} className="shrink-0" />
          <span className="truncate">New Chat</span>
        </Button>

        <div className="flex-1 overflow-y-auto space-y-1 min-w-0 pr-1">
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 px-2">
            Recent Threads
          </h2>

          {threadsData.map((thread) => (
            <Link
              key={thread.thread_id}
              href={`/thread/${thread.thread_id}`}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group relative",
                threadId === thread.thread_id
                  ? "bg-zinc-800 text-zinc-100"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              )}
            >
              <MessageSquareIcon size={18} className="shrink-0" />
              <span className="truncate text-sm font-medium flex-1">
                {thread.title || "Untitled Chat"}
              </span>
              <button
                onClick={(e) => handleDelete(e, thread.thread_id)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity shrink-0 flex items-center justify-center"
                aria-label={`Delete ${thread.title || "Untitled Chat"}`}
              >
                <Trash2Icon size={14} />
              </button>
            </Link>
          ))}

          {threadsData.length === 0 && (
            <p className="text-sm text-zinc-500 px-2 italic">No chats yet</p>
          )}
        </div>
      </div>

      <button
        onClick={toggleCollapsed}
        className={cn(
          "absolute top-6 z-20 flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-700 transition-all duration-300 shadow-sm",
          isCollapsed ? "-right-10" : "-right-3"
        )}
        aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <ChevronLeftIcon size={14} className={cn("transition-transform duration-300", isCollapsed && "rotate-180")} />
      </button>
    </div>
  );
}