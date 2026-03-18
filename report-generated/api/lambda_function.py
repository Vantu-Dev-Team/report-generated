"""AWS Lambda handler — Mangum adapter for the FastAPI app."""

from mangum import Mangum

from app import app

handler = Mangum(app, lifespan="off")
