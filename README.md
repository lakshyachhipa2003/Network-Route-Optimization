# Network Route Optimizer

A Python 3.12+ Django REST Framework API for a directed network. Create nodes and
positive-latency edges, find the minimum-latency route using Dijkstra, and query
persistent route history. Includes every required and optional assignment API.

## Stack and layout

Django 5.2 LTS, DRF 3.16, PostgreSQL via psycopg 3 (SQLite for local development),
drf-spectacular, and Django/DRF's unittest-based test runner. `requirements.txt`
pins the exact dependency versions used during verification.

```text
.
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── network/
    ├── __init__.py
    ├── admin.py
    ├── models.py
    ├── serializers.py
    ├── views.py
    ├── urls.py
    ├── migrations/
    │   ├── __init__.py
    │   └── 0001_initial.py
    ├── services/
    │   ├── __init__.py
    │   └── route_optimizer.py
    └── tests/
        ├── __init__.py
        ├── test_nodes.py
        ├── test_edges.py
        ├── test_shortest_route.py
        └── test_route_history.py
```

## Installation

Run from this repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Put the generated value in `.env` as `DJANGO_SECRET_KEY`, then:

```bash
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/api/docs/ for Swagger UI. The OpenAPI schema is at
http://127.0.0.1:8000/api/schema/. Swagger's UI assets require internet access.
The API needs no authentication, as specified by the assignment. The optional
Django admin at `/admin/` uses Django's normal staff authentication; create an
admin account with `python manage.py createsuperuser` if needed.

### Environment

Settings load `.env` automatically; existing process variables take precedence.
`DJANGO_SECRET_KEY` is required, with no hardcoded fallback. `DJANGO_DEBUG`
defaults to false; `.env.example` enables it for local development.
`DJANGO_ALLOWED_HOSTS` is comma-separated and defaults to localhost/127.0.0.1.
UTC and timezone-aware timestamps are enabled.

For PostgreSQL, provision an empty database and a role that owns it, then set:

```dotenv
DB_ENGINE=postgresql
DB_NAME=network_routes
DB_USER=network_routes
DB_PASSWORD=your-database-password
DB_HOST=localhost
DB_PORT=5432
```

Run `python manage.py migrate` against the selected database. The PostgreSQL test
runner needs permission to create its temporary test database. SQLite is the
default when `DB_ENGINE=sqlite`; no database service is needed.

For deployment, supply a private secret, disable DEBUG, set explicit allowed
hosts, serve through an ASGI/WSGI production server, configure HTTPS, and set
`DJANGO_SECURE_SSL_REDIRECT=true`. Secure session/CSRF cookies are enabled when
DEBUG is false. Only configure proxy trust settings when the proxy is trusted.
`python manage.py check --deploy` reports additional deployment requirements,
including HSTS, which should be chosen for the actual hosting environment.

## API

Paths have **no trailing slash**. All bodies and responses use JSON.

| Method | Path | Success | Purpose |
|---|---|---|---|
| POST | `/nodes` | 201 | Create a node |
| GET | `/nodes` | 200 | List nodes by ID |
| DELETE | `/nodes/{id}` | 204 | Delete node and incident edges |
| POST | `/edges` | 201 | Create directed edge |
| GET | `/edges` | 200 | List edges by ID |
| DELETE | `/edges/{id}` | 204 | Delete edge |
| POST | `/routes/shortest` | 200 | Compute and record minimum-latency route |
| GET | `/routes/history` | 200 | List/filter saved successful queries |

### Nodes and edges

```bash
curl -X POST http://127.0.0.1:8000/nodes \
  -H 'Content-Type: application/json' -d '{"name":"ServerA"}'
curl -X POST http://127.0.0.1:8000/nodes \
  -H 'Content-Type: application/json' -d '{"name":"ServerB"}'
curl -X POST http://127.0.0.1:8000/edges \
  -H 'Content-Type: application/json' \
  -d '{"source":"ServerA","destination":"ServerB","latency":12.5}'
```

Node response: `{"id":1,"name":"ServerA"}`. Edge response:

```json
{"id":1,"source":"ServerA","destination":"ServerB","latency":12.5}
```

Names are case-sensitive, trimmed, nonblank, and at most 255 characters. Duplicate
names return 400. Source/destination refer to existing node names. Missing nodes,
duplicate directed edges, self-connections, invalid numbers, and latency <= 0
return 400. The reverse edge is a separate connection. Latency supports up to
12 integer digits and six decimal places; extra fractional digits are rejected
rather than silently rounded. Nonfinite values are rejected.

List responses are arrays containing the same object shapes as create responses.
Deletion returns an empty 204 response, or 404 if the ID does not exist.

```bash
curl http://127.0.0.1:8000/nodes
curl http://127.0.0.1:8000/edges
curl -X DELETE http://127.0.0.1:8000/edges/1
curl -X DELETE http://127.0.0.1:8000/nodes/1
```

### Shortest route

```bash
curl -X POST http://127.0.0.1:8000/routes/shortest \
  -H 'Content-Type: application/json' \
  -d '{"source":"ServerA","destination":"ServerB"}'
```

```json
{"total_latency":12.5,"path":["ServerA","ServerB"]}
```

Both endpoints must exist or the response is 400. A valid same-node query returns
zero latency and a one-node path, and is saved. A disconnected route returns 404:

```json
{"error":"No path exists between ServerA and ServerD"}
```

Unsuccessful queries are not saved. Validation errors use DRF's field-to-error-list
format, for example `{"name":["This field is required."]}`; cross-field errors use
`non_field_errors`. Database integrity races return a 400 validation error.

### Route history

```bash
curl --get http://127.0.0.1:8000/routes/history \
  --data-urlencode 'source=ServerA' \
  --data-urlencode 'destination=ServerB' \
  --data-urlencode 'limit=10' \
  --data-urlencode 'date_from=2026-01-01T00:00:00Z' \
  --data-urlencode 'date_to=2026-12-31T23:59:59Z'
```

```json
[
  {
    "id":1,
    "source":"ServerA",
    "destination":"ServerB",
    "total_latency":12.5,
    "path":["ServerA","ServerB"],
    "created_at":"2026-11-01T00:00:00Z"
  }
]
```

All five filters are optional and combine with AND. Source/destination match
exact stored names; an unknown name returns an empty array. `limit` must be an
integer from 1 through 10,000. Dates are ISO 8601 timestamps with inclusive bounds;
timezone offsets are accepted, and offset-free timestamps are interpreted as UTC.
A reversed date range or malformed filter returns 400. Results are ordered newest
first, then by descending ID to break timestamp ties. Without limit, all matching
rows are returned; list endpoints are intentionally unpaginated to match the PDF.

## Design and algorithm

`Node` has a unique name and creation timestamp. `Edge` holds source/destination
foreign keys and a fixed-point decimal latency. Database checks enforce positive
latency and disallow self-loops; a unique pair constraint prevents duplicate
directed edges. The unique pair index supports source lookups, and Django indexes
the foreign keys. Serializer checks provide readable errors before insertion;
creation uses an atomic block with an integrity-error fallback for races.

`RouteHistory` stores source/destination **name snapshots**, JSON path snapshots,
and total latency, rather than cascading foreign keys. Deleting graph elements
leaves historical responses intact, including intermediate node names. Recreating
a node with the same name does not change old records. History has indexes on
source, destination, creation time, and a combined source/destination/time index.
Filtering and limiting happen in SQL. Edge listing uses `select_related`, and
history queries require no related-object queries.

The pure `shortest_path` function takes an iterable of `(source, destination,
Decimal latency)` tuples. It builds an adjacency list, puts the source into a
`heapq` minimum heap, and repeatedly relaxes outgoing edges. Stale heap entries
are skipped. Predecessor pointers reconstruct the ordered path once the destination
is popped; it never enumerates complete candidate paths. Parallel edges are
supported by the algorithm even though the API prohibits duplicate connections.
For equal minimum costs, any minimum path is valid; stable edge ordering and heap
node-name ties make results reproducible for a fixed graph.

The lazy-heap implementation uses **O((V + E) log(V + E)) time** and **O(V + E)
space**, including adjacency storage and heap entries. For a simple directed graph
this is conventionally written O((V + E) log V). Decimal weights preserve exact
six-place sums during calculation and database storage. Responses contain JSON
numbers to match the assignment; clients needing decimal arithmetic should parse
these numbers using a decimal-capable JSON parser.

Views validate input and coordinate the pure service and persistence. Graph edges
are loaded with one joined query; concurrent graph edits do not rewrite saved
history. A route describes the graph rows read for that request; the API does not
lock the graph against concurrent edits. Each successful query inserts a single
history row. No authentication or unrelated application features are introduced.

## Verification

```bash
python manage.py test -v 2
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate --fail-on-warn --file openapi.yaml
```

Tests cover creation, validation, direct database constraints, list/delete APIs,
history retention, combined/individual filters, inclusive dates, limits, query
counts, Swagger/schema availability, and independent algorithm cases: direct,
indirect, disconnected, same-node, directed, parallel edges, cycles, exact decimal
sums, equal minima, invalid weights, and a graph with 5,001 nodes/9,999 edges.

Actual initial verification: **23 tests passed on Python 3.12 with SQLite**.
PostgreSQL configuration and driver are included; PostgreSQL execution was not
verified because this environment has no PostgreSQL server installed.
