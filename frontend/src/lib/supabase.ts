import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;

if (!url || !key) {
  console.warn(
    "VITE_SUPABASE_URL / VITE_SUPABASE_PUBLISHABLE_KEY 가 없습니다. frontend/.env 를 확인하세요.",
  );
}

export const supabase = createClient(url ?? "", key ?? "");

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";
