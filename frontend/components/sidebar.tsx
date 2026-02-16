"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  useGetThreadsApiThreadsGet,
  getGetThreadsApiThreadsGetQueryKey,
  useDeleteThreadApiThreadsThreadIdDelete
} from "@/lib/api/default/default";
import { PlusIcon, MessageSquareIcon, ChevronLeftIcon, ChevronRightIcon, Trash2Icon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

type ThreadInfo = {
  thread_id: string;
  title: string;
  created_at: string;
};

type GetThreadsResponse = {
  threads: ThreadInfo[];
};

export function Sidebar() {
  const { threadId } = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const { data } = useGetThreadsApiThreadsGet();
  const { mutate: deleteThread } = useDeleteThreadApiThreadsThreadIdDelete({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({
          queryKey: getGetThreadsApiThreadsGetQueryKey(),
        });
        if (threadId) {
          router.push("/");
        }
      },
    },
  });

  const threadsData = data?.status === 200 ? (data.data as GetThreadsResponse).threads : [];

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this thread?")) {
      deleteThread({ threadId: id });
    }
  };

  return (
    <div
      className={cn(
        "relative flex flex-col h-screen bg-zinc-900 border-r border-zinc-800 text-zinc-100 p-4 transition-all duration-300 ease-in-out",
        isCollapsed ? "w-20" : "w-64"
      )}
    >
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-10 z-10 flex h-6 w-6 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 text-zinc-400 hover:text-zinc-100"
      >
        {isCollapsed ? <ChevronRightIcon size={14} /> : <ChevronLeftIcon size={14} />}
      </button>

      <Button
        onClick={() => router.push("/")}
        className={cn(
          "mb-6 flex items-center justify-start gap-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border-zinc-700",
          isCollapsed ? "px-0 justify-center h-10 w-10 mx-auto" : "w-full"
        )}
      >
        <PlusIcon size={18} />
        {!isCollapsed && <span>New Chat</span>}
      </Button>

      <div className="flex-1 overflow-y-auto space-y-1">
        {!isCollapsed && (
          <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2 px-2">
            Recent Threads
          </h2>
        )}
        {threadsData.map((thread) => (
          <Link
            key={thread.thread_id}
            href={`/thread/${thread.thread_id}`}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg transition-colors group relative",
              threadId === thread.thread_id
                ? "bg-zinc-800 text-zinc-100"
                : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100",
              isCollapsed && "justify-center"
            )}
          >
            <MessageSquareIcon size={18} className="shrink-0" />
            {!isCollapsed && (
              <>
                <span className="truncate text-sm font-medium flex-1">
                  {thread.title || "Untitled Chat"}
                </span>
                <button
                  onClick={(e) => handleDelete(e, thread.thread_id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-opacity"
                >
                  <Trash2Icon size={14} />
                </button>
              </>
            )}
          </Link>
        ))}
        {threadsData.length === 0 && !isCollapsed && (
          <p className="text-sm text-zinc-500 px-2 italic">No chats yet</p>
        )}
      </div>
    </div>
  );
}
