import { NextRequest, NextResponse } from "next/server";
import { getSessionId } from "@/actions/get-session-id";

const API_URL = process.env.FASTAPI_URL;

export async function proxy(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  try {
    const { path: pathArray } = await params;

    const path = pathArray.join('/');
    const searchParams = req.nextUrl.searchParams.toString();
    const finalURL = `${API_URL}/${path}${searchParams ? `?${searchParams}` : ""}`;

    const headers = new Headers(req.headers);
    headers.delete("host");
    const guestId = await getSessionId();
    headers.set("x-guest-id", guestId);

    const res = await fetch(finalURL, {
      method: req.method,
      headers: headers,
      body: req.body,
      cache: 'no-store',
      // @ts-ignore
      duplex: 'half',
    });

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: res.headers
    });

  } catch (error) {
    console.error("Proxy Error:", error);
    return NextResponse.json({ error: "Upstream Proxy Error" }, { status: 502 });
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE, proxy as PATCH };