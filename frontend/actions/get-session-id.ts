"use server";

import { getIronSession } from "iron-session";
import { sessionOptions, SessionData } from "@/lib/session";
import { cookies } from "next/headers";

export async function getSessionId() {
  const session = await getIronSession<SessionData>(await cookies(), sessionOptions);
  return session.guestId;
}