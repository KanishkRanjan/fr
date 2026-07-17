"""HTTP API for the ER diagram validator.

    uvicorn er_validator.api:app --port 8000

POST /validate
    body: {"teacher": <editor export json>, "student": <editor export json>,
           "algorithm": "bliss"   (optional)}
    200 -> {"is_valid", "algorithm_used", "mismatches", "names", "stats"}
    422 -> malformed diagram / unknown algorithm
    500 -> native engine failure

POST /compare-names
    body: {"teacher": [names], "student": [names],
           "weights"?, "penalties"?, "similarity_threshold"?, "custom_ontology"?}
    200 -> {"score", "matched", "missing", "extra", "scoring_breakdown"}

Portal question storage (see store.py):

GET    /questions                 -> [{"id", "title", "created_at"}]
POST   /questions                 body: {"title", "prompt", "reference"} -> {"id"}
GET    /questions/{id}            -> question; add ?include_reference=true for the
                                     teacher's reference diagram
DELETE /questions/{id}            -> {"ok": true}
POST   /questions/{id}/submit     body: {"student", "algorithm"?} -> validate() result
"""
import os

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import EngineError, SchemaError, validate, __version__
from .core import default_algorithm
from .engines import ENGINES
from .name_matcher import DEFAULT_SIMILARITY_THRESHOLD, compare_entities
from . import store

app = FastAPI(title='ER Diagram Validator', version=__version__)
store.init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in
                   os.environ.get('CORS_ORIGINS', '*').split(',')],
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


@app.post('/compare-names')
def compare_names_endpoint(payload: dict = Body(...)):
    teacher = payload.get('teacher')
    student = payload.get('student')
    if not isinstance(teacher, list) or not isinstance(student, list):
        raise HTTPException(422, 'body must contain "teacher" and "student" arrays of names')
    return compare_entities(
        teacher, student,
        weights=payload.get('weights'),
        penalties=payload.get('penalties'),
        similarity_threshold=payload.get('similarity_threshold', DEFAULT_SIMILARITY_THRESHOLD),
        custom_ontology=payload.get('custom_ontology') or (),
    )


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
