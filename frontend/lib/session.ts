import { SessionOptions } from "iron-session";

export interface SessionData {
  guestId: string;
}

export const sessionOptions: SessionOptions = {
  password: process.env.SESSION_PASSWORD || "",
  cookieName: "guest_session_id",
  cookieOptions: {
    secure: process.env.NODE_ENV === "production", // Only send over HTTPS in prod
    httpOnly: true, // Prevents JavaScript access (XSS protection)
    sameSite: "lax", // CSRF protection
    maxAge: 60 * 60 * 24 * 30, // 30 days
  },
};