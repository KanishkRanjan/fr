"""Parse and validate the drawdb-clone editor's JSON export into typed objects."""
from dataclasses import dataclass, field


class SchemaError(ValueError):
    """Raised when an incoming diagram document is malformed."""


VALID_CARDINALITIES = {'one_to_one', 'one_to_many', 'many_to_one'}


@dataclass
class Field:
    id: int
    name: str
    type: str
    pk: bool
    not_null: bool
    unique: bool
    increment: bool
    default: str


@dataclass
class Table:
    id: int
    name: str
    fields: list


@dataclass
class Relationship:
    id: int
    cardinality: str
    start_table: int
    start_field: int
    end_table: int
    end_field: int


@dataclass
class Diagram:
    title: str
    tables: list = field(default_factory=list)
    relationships: list = field(default_factory=list)


def _require(cond, msg):
    if not cond:
        raise SchemaError(msg)


def parse_diagram(doc, who='diagram'):
    """doc: the dict exported by the editor. Raises SchemaError with a human message."""
    _require(isinstance(doc, dict), f'{who}: expected a JSON object')
    _require(isinstance(doc.get('tables'), list), f'{who}: missing "tables" array')
    _require(isinstance(doc.get('relationships'), list), f'{who}: missing "relationships" array')

    tables = []
    field_owner = {}   # field id -> table id
    table_ids = set()
    for ti, t in enumerate(doc['tables']):
        _require(isinstance(t, dict), f'{who}: tables[{ti}] is not an object')
        _require(isinstance(t.get('id'), int), f'{who}: tables[{ti}] has no integer "id"')
        _require(t['id'] not in table_ids, f'{who}: duplicate table id {t["id"]}')
        table_ids.add(t['id'])
        _require(isinstance(t.get('fields'), list), f'{who}: table "{t.get("name", t["id"])}" has no "fields" array')
        fields = []
        for fi, f in enumerate(t['fields']):
            _require(isinstance(f, dict) and isinstance(f.get('id'), int),
                     f'{who}: table "{t.get("name")}" fields[{fi}] is malformed')
            _require(f['id'] not in field_owner, f'{who}: duplicate field id {f["id"]}')
            _require(isinstance(f.get('type'), str) and f['type'].strip(),
                     f'{who}: field "{f.get("name")}" in table "{t.get("name")}" has no type')
            field_owner[f['id']] = t['id']
            fields.append(Field(
                id=f['id'],
                name=str(f.get('name', '')),
                type=f['type'].strip().upper(),
                pk=bool(f.get('pk')),
                not_null=bool(f.get('notNull')),
                unique=bool(f.get('unique')),
                increment=bool(f.get('increment')),
                default=str(f.get('def', '')),
            ))
        tables.append(Table(id=t['id'], name=str(t.get('name', '')), fields=fields))

    relationships = []
    for ri, r in enumerate(doc['relationships']):
        _require(isinstance(r, dict), f'{who}: relationships[{ri}] is not an object')
        card = r.get('cardinality', 'many_to_one')
        _require(card in VALID_CARDINALITIES,
                 f'{who}: relationships[{ri}] has unknown cardinality "{card}"')
        for end, tkey, fkey in (('start', 'startTable', 'startField'), ('end', 'endTable', 'endField')):
            _require(isinstance(r.get(tkey), int) and isinstance(r.get(fkey), int),
                     f'{who}: relationships[{ri}] is missing {end} table/field ids')
            _require(r[tkey] in table_ids,
                     f'{who}: relationships[{ri}] references unknown table id {r[tkey]}')
            _require(field_owner.get(r[fkey]) == r[tkey],
                     f'{who}: relationships[{ri}] {end}Field {r[fkey]} does not belong to table {r[tkey]}')
        # Canonicalize drawing direction: "A -(one_to_many)-> B" is the same
        # picture as "B -(many_to_one)-> A" ('1' on one table, 'n' on the other),
        # so normalize every one_to_many into a flipped many_to_one. Which way
        # the user dragged must never affect validation.
        if card == 'one_to_many':
            card = 'many_to_one'
            r = {**r, 'startTable': r['endTable'], 'startField': r['endField'],
                 'endTable': r['startTable'], 'endField': r['startField']}
        relationships.append(Relationship(
            id=r.get('id', ri),
            cardinality=card,
            start_table=r['startTable'],
            start_field=r['startField'],
            end_table=r['endTable'],
            end_field=r['endField'],
        ))

    return Diagram(title=str(doc.get('title', '')), tables=tables, relationships=relationships)
