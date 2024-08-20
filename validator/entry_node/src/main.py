# TODO: Do we need connection pools with redis?
from fastapi import FastAPI
import uvicorn
from validator.entry_node.src.text.main import router as text_router


app = FastAPI(debug=False)

app.include_router(text_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
