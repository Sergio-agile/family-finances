# Chuleta: de Rails a FastAPI

Notas de aprendizaje. Cada concepto nuevo que aparezca en un PR se añade aquí.

## Herramientas

| Rails / Ruby | Python / FastAPI | En este repo |
|---|---|---|
| RVM / rbenv | `uv python install` | `backend/.python-version` |
| `Gemfile` | `pyproject.toml` | `backend/pyproject.toml` |
| `Gemfile.lock` | `uv.lock` | `backend/uv.lock` |
| `bundle add x` | `uv add x` (`--dev` para desarrollo) | |
| `bundle install` | `uv sync` | |
| `bundle exec x` | `uv run x` | `uv run pytest` |
| gems aisladas por proyecto | entorno virtual `.venv/` | lo crea uv, no se sube a git |
| `rails s` | `uv run fastapi dev app/main.py` | recarga al guardar, como en dev |
| Rubocop | Ruff (lint + formato) | `uv run ruff check .` |
| RSpec / Minitest | pytest | `backend/tests/` |
| `config/database.yml` + ENV | `pydantic-settings` | `backend/app/config.py` |

## Conceptos del PR 1

### La app y las rutas — `app/main.py`
En Rails tienes `routes.rb` y un controlador por separado. En FastAPI la ruta va pegada a la función con un decorador:

```python
@app.get("/api/health")          # ≈ get "/api/health", to: "health#show"
def health(...) -> Health:       # ≈ HealthController#show
```

### Modelos de respuesta — Pydantic
`class Health(BaseModel)` define la forma exacta del JSON de salida. Es una mezcla de serializer y strong params: valida, convierte tipos y genera la documentación. Abre `http://localhost:8000/docs` con el backend arrancado: esa página (Swagger) sale sola de esos modelos.

### Inyección de dependencias — `Depends()`
```python
def health(session: Annotated[Session, Depends(get_session)]):
```
FastAPI llama a `get_session()` antes de tu función y te pasa el resultado. Es el equivalente a un `before_action` que prepara algo (como `current_user`), pero explícito en la firma: viendo los parámetros sabes de qué depende el endpoint. En los tests se puede sustituir por una versión falsa.

`get_session` usa `yield`: lo de antes del `yield` se ejecuta antes de la petición y lo de después, al terminar (cierra la sesión). Como un `around_action`.

### Sesión de SQLAlchemy — `app/db.py`
En ActiveRecord la conexión es implícita (`Expense.all` y listo). En SQLAlchemy trabajas con una **sesión** explícita: abres, haces consultas, haces commit y cierras. Es más verboso, pero se ve claramente qué pasa en cada transacción. Lo veremos a fondo con el primer modelo.

### Type hints
`-> Health`, `session: Session`… Python no los comprueba al ejecutarse, pero FastAPI los **usa** para validar la entrada y la salida, y el editor para autocompletar. Aquí no son decoración.

## Preguntas para revisar el PR 1
1. ¿Qué devuelve `/api/health` si Postgres está caído? ¿Es lo que querrías que viera un sistema de monitorización?
2. ¿Por qué el frontend llama a `/api/health` y no a `http://localhost:8000/api/health`? (pista: `vite.config.ts`)
