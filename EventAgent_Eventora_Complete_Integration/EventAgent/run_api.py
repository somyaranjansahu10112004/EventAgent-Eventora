"""Start the EventAgent API for local dashboard use."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("eventagent.api.app:app", host="127.0.0.1", port=8000, reload=False)
