import { create } from 'zustand';

interface ChatStore {
  remountKey: number;
  newChat: () => void;
}

export const useChatStore = create<ChatStore>((set) => ({
  remountKey: 0,
  newChat: () => set((state) => ({ remountKey: state.remountKey + 1 })),
}));
