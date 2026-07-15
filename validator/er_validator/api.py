"""HTTP API for the ER diagram validator.

    uvicorn er_validator.api:app --port 8000

POST /validate
    body: {"teacher": <editor export json>, "student": <editor export json>,
           "algorithm": "bliss" | "saucy"   (optional)}
    200 -> {"is_valid", "algorithm_used", "mismatches", "stats"}
    422 -> malformed diagram / unknown algorithm
    500 -> native engine failure

Portal question storage (see store.py):

GET    /questions                 -> [{"id", "title", "created_at"}]
POST   /questions                 body: {"title", "prompt", "reference"} -> {"id"}
GET    /questions/{id}            -> question; add ?include_reference=true for the
                                     teacher's reference diagram
DELETE /questions/{id}            -> {"ok": true}
POST   /questions/{id}/submit     body: {"student", "algorithm"?} -> validate() result
"""
from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import EngineError, SchemaError, validate, __version__
from .core import default_algorithm
from .engines import ENGINES
from . import store

app = FastAPI(title='ER Diagram Validator', version=__version__)
store.init_db()

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


@app.get('/questions')
def questions_list():
    return store.list_questions()


@app.post('/questions')
def questions_create(payload: dict = Body(...)):
    title = payload.get('title')
    prompt = payload.get('prompt')
    reference = payload.get('reference')
    if not title or not prompt or reference is None:
        raise HTTPException(422, 'body must contain "title", "prompt" and "reference"')
    return {'id': store.create_question(title, prompt, reference)}


@app.get('/questions/{qid}')
def questions_get(qid: int, include_reference: bool = False):
    q = store.get_question(qid)
    if q is None:
        raise HTTPException(404, f'no question with id {qid}')
    if not include_reference:
        del q['reference']
    return q


@app.delete('/questions/{qid}')
def questions_delete(qid: int):
    if not store.delete_question(qid):
        raise HTTPException(404, f'no question with id {qid}')
    return {'ok': True}


@app.post('/questions/{qid}/submit')
def questions_submit(qid: int, payload: dict = Body(...)):
    q = store.get_question(qid)
    if q is None:
        raise HTTPException(404, f'no question with id {qid}')
    student = payload.get('student')
    if student is None:
        raise HTTPException(422, 'body must contain a "student" diagram object')
    try:
        return validate(q['reference'], student, payload.get('algorithm'))
    except SchemaError as e:
        raise HTTPException(422, str(e))
    except EngineError as e:
        raise HTTPException(500, str(e))
