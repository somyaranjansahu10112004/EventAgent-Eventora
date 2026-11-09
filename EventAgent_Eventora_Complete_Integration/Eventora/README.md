# Eventora — AI-powered event discovery

A responsive event discovery application based on the uploaded `Today's Lead(1).csv`, with React + Vite + TypeScript on the frontend and Express + Groq on the backend.

## Included
- Premium dark-first glassmorphism UI with a persistent light/dark toggle.
- Event cards, detail modal, search, category/location/date filters, and sorting.
- Floating AI chat panel with suggested questions, loading/error states, and matching event cards.
- Backend event API, category/location metadata endpoints, request validation, chat rate limiting, and Groq integration.
- CSV-derived `server/data/events.json` with original fields preserved alongside normalized values.
- No fabricated event listings, ratings, attendance numbers, or registration confirmations.

## Dataset notes
The uploaded sheet contained **39 rows and 13 columns**. The `Unnamed: 12` column was mostly empty but contained numeric values in a few rows, so it is retained as `extraColumn` rather than silently discarded. Two event names are missing; five venues, 14 areas, nine times, 16 registration fields, six hosts, 15 Instagram IDs, and 19 prices are missing. `NA` prices are treated as unknown, not free. Dates were parsed using the sheet's `DD-MM-YYYY` format and stored as ISO dates while retaining `originalDate`. Source URLs are normalized to the first URL-looking token while the original source field is preserved. The source sheet has repeated event names and repeated URLs; records are not merged automatically because these may represent separate listings.

The CSV dates mostly fall in August–September 2026, which are past relative to 26 October 2026. The site defaults to upcoming events and may therefore show only the genuinely future listings. Use the “All dates” filter to inspect the full imported dataset. Confirm source listings before attending because this app does not independently verify event changes.

## Requirements
- Node.js 20+ recommended
- npm
- A Groq API key for live AI answers (the site and event API still run without it; the chatbot returns a dataset-based fallback)

## Run locally
1. Extract the project folder.
2. Install root dependencies:
   ```bash
   npm install
   npm install --prefix client
   npm install --prefix server
   ```
3. Copy `.env.example` to `server/.env`.
4. Add your Groq API key to `server/.env`:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   PORT=5000
   CLIENT_ORIGIN=http://localhost:5173
   DEFAULT_TIMEZONE=Asia/Kolkata
   ```
   Check Groq's current model availability and set `GROQ_MODEL` to a supported chat model if needed.
5. Start both apps:
   ```bash
   npm run dev
   ```
6. Open http://localhost:5173. The API runs at http://localhost:5000.

## Environment variables
- `GROQ_API_KEY`: server-only Groq secret. Never use a `VITE_` prefix.
- `GROQ_MODEL`: supported Groq chat model identifier.
- `PORT`: backend port, defaults to 5000.
- `CLIENT_ORIGIN`: comma-separated allowed frontend origins.
- `DEFAULT_TIMEZONE`: date comparison timezone, defaults to Asia/Kolkata.
- Optional frontend `VITE_API_URL`: API base URL, defaults to `http://localhost:5000`.

## API
- `GET /api/health` — service health, loaded record count, current local date.
- `GET /api/events` — upcoming events by default; supports `q`, `category`, `city`, `from`, `to`, `free=true`, `page`, `limit`. Use `includePast=true` to include past and undated records.
- `GET /api/events/:id` — one event by stable ID.
- `GET /api/categories` — distinct categories in the imported data.
- `GET /api/locations` — distinct cities in the imported data.
- `POST /api/chat` — body `{ "message": "What events are coming up?", "conversationId": "optional", "timezone": "Asia/Kolkata" }`.

The current prototype uses a normalized JSON file so it can run without MongoDB. To add persistence later, replace the data access functions with a MongoDB/Mongoose repository without changing the frontend API contract.

## Updating event data
A basic CSV importer is included. From the `server/` directory, run `npm run import:csv -- "../Today's Lead(1).csv"`. It writes `data/events.json`, preserves original source fields, validates DD-MM-YYYY dates, and prints a small import summary. Back up and review the existing JSON before running it; generated IDs follow row order, so review duplicates before production use. The uploaded original CSV is not modified by this project. For a production CSV import workflow, implement an authenticated admin-only importer with schema validation, duplicate review, an audit report, and safe atomic file/database writes. This starter deliberately does **not** expose an unauthenticated import endpoint.

## Deployment
- Frontend: deploy `client/` to Vercel; set `VITE_API_URL` to your deployed backend URL.
- Backend: deploy `server/` to Render or another Node host; set the environment variables above. Ensure `server/data/events.json` is included in the deployment.
- Build frontend: `npm run build --prefix client`.
- Build backend: `npm run build --prefix server` (start command after build: `npm start --prefix server`; confirm the host runs from the server directory or adjust the start command accordingly).

Set `CLIENT_ORIGIN` to the exact deployed frontend origin. Never commit `.env` files. Configure HTTPS for production.

## Current limitations / recommended next steps
- Event descriptions and image URLs are absent from the sheet, so the cards use generated typographic artwork rather than invented event photos or descriptions.
- Registration links are not a separate column. The source URL is shown as “Open original listing”; do not assume it is a registration URL.
- Admin authentication, persistent chat history, MongoDB storage, and a production CSV import UI are not included in this initial prototype.
- The chat uses bounded record retrieval and a concise context window. For production-scale datasets, improve intent extraction and retrieval (e.g., deterministic date-range/category filters plus indexed search) and add tests for date boundaries and CSV import behavior.

## Troubleshooting
- If the frontend says it cannot reach the event service, check that the backend started on port 5000 and `CLIENT_ORIGIN` matches the frontend URL.
- If chat reports that Groq is not configured, create `server/.env` and set `GROQ_API_KEY`.
- If Groq returns an error, verify the model ID and key against the current Groq dashboard.
- If a port is busy, change `PORT` and update `VITE_API_URL` accordingly.
