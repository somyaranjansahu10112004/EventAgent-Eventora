import pg from 'pg';
const { Pool } = pg;
export const databaseEnabled = Boolean(process.env.DATABASE_URL);
export const pool = databaseEnabled ? new Pool({ connectionString: process.env.DATABASE_URL, ssl: process.env.PGSSLMODE === 'require' ? { rejectUnauthorized: false } : undefined, max: 5, idleTimeoutMillis: 30000, connectionTimeoutMillis: 5000 }) : null;
export async function loadPublishedEvents<T>(): Promise<T[] | null> {
  if (!pool) return null;
  const result = await pool.query(`SELECT id, event_name AS "eventName", category, venue, area, city, to_char(event_date, 'YYYY-MM-DD') AS date, original_date AS "originalDate", event_time AS time, registration_required AS "registrationRequired", source_url AS "sourceUrl", original_source_value AS "originalSourceValue", price, host_name AS "hostName", instagram_id AS "instagramId", NULL::text AS "extraColumn" FROM events WHERE is_published = TRUE AND status = 'published' ORDER BY event_date ASC NULLS LAST`);
  // A successful full read confirms the public application has consumed the
  // latest committed event state. Outbox remains an audit/retry trail.
  await pool.query(`UPDATE sync_outbox SET status='delivered', delivered_at=NOW(), last_error=NULL
    WHERE status IN ('pending','failed') AND created_at <= NOW()`);
  return result.rows as T[];
}
