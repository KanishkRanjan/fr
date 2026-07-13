"""HTTP API for the ER diagram validator.

    uvicorn er_validator.api:app --port 8000

POST /validate
    body: {"teacher": <editor export json>, "student": <editor export json>,
           "algorithm": "bliss" | "saucy"   (optional)}
    200 -> {"is_valid", "algorithm_used", "mismatches", "stats"}
    422 -> malformed diagram / unknown algorithm
    500 -> native engine failure
"""
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import EngineError, SchemaError, validate, __version__
from .core import default_algorithm
from .engines import ENGINES

app = FastAPI(title='ER Diagram Validator', version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:5173', 'http://127.0.0.1:5173',
    ],
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.get('/health')
def health():
    engines = {}
    for key, cls in ENGINES.items():
        try:
            cls().binary()
            engines[key] = 'ready'
        except EngineError as e:
            engines[key] = f'unavailable: {e}'
    return {'ok': all(v == 'ready' for v in engines.values()),
            'default_algorithm': default_algorithm(),
            'engines': engines}


@app.post('/validate')
def validate_endpoint(payload: dict = Body(...)):
    teacher = payload.get('teacher')
    student = payload.get('student')
    if teacher is None or student is None:
        raise HTTPException(422, 'body must contain "teacher" and "student" diagram objects')
    try:
        return validate(teacher, student, payload.get('algorithm'))
    except SchemaError as e:
        raise HTTPException(422, str(e))
    except EngineError as e:
        raise HTTPException(500, str(e))
