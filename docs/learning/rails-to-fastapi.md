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

## Conceptos del PR 2: modelos, migraciones y CRUD

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `class Expense < ApplicationRecord` | `class Expense(Base)` (SQLAlchemy) | `app/models.py` |
| `belongs_to :category` | `relationship()` + `ForeignKey` | `Expense.category` |
| `rails g migration` / `db:migrate` | `alembic revision --autogenerate` / `alembic upgrade head` | `migrations/versions/` |
| `db/schema.rb` | no existe: el modelo es la fuente de verdad y Alembic compara | |
| `rails db:seed` | `uv run python -m app.seed` | `app/seed.py` |
| `validates :amount, numericality: { greater_than: 0 }` | `Field(gt=0)` en el esquema Pydantic | `app/schemas.py` |
| `config/routes.rb` + `resources :expenses` | `APIRouter` + `app.include_router()` | `app/routers/` |
| `includes(:category)` (evitar N+1) | `.options(selectinload(Expense.category))` | `list_expenses` |
| `use_transactional_tests` + BD de test | fixture `session` con rollback + `family_finances_test` | `tests/conftest.py` |
| factories / fixtures | fixtures de pytest (`groceries`) | `tests/conftest.py` |

### Modelo y esquema son cosas distintas
Es la diferencia más importante con Rails. En ActiveRecord el modelo lo hace todo: tabla, validaciones y serialización. Aquí hay **dos capas**:
- **Modelo SQLAlchemy** (`models.py`): cómo se guarda en la base de datos.
- **Esquemas Pydantic** (`schemas.py`): qué entra y qué sale por la API. `ExpenseCreate` es lo que acepta el POST (como strong params más validaciones) y `ExpenseRead` es lo que devuelve (como un serializer).

Es más código, pero la API no cambia cuando cambias una columna, y nadie puede colar un `id` o un `created_at` en el POST: `ExpenseCreate` simplemente no los tiene.

`from_attributes=True` permite construir el esquema directamente desde un objeto del modelo. Por eso el endpoint puede devolver un `Expense` y FastAPI lo convierte en `ExpenseRead`.

### `Mapped[int]`: los tipos definen las columnas
`amount_cents: Mapped[int]` ya es una columna `INTEGER NOT NULL`. Si pusieras `Mapped[int | None]`, la columna admitiría NULL. El tipo de Python y la columna no pueden desincronizarse.

### La sesión y el commit explícito
```python
session.add(expense)    # ≈ expense = Expense.new(...)
session.commit()        # ≈ expense.save!, pero guarda TODO lo pendiente en la sesión
session.refresh(expense)  # recarga id y created_at, que los genera la base de datos
```

### Migraciones autogeneradas
Alembic compara `models.py` con la base de datos y escribe la migración. **Revísala siempre**: no detecta renombrados (los ve como borrar y crear, y perderías los datos) y a veces se le escapan detalles. Un ejemplo de este PR: la primera versión creaba `created_at` sin zona horaria, la corregí en el modelo y regeneré la migración.

### Tests contra Postgres real, en una transacción
`conftest.py` crea `family_finances_test`, le aplica las migraciones y ejecuta cada test dentro de una transacción que se deshace al terminar. Es justo lo que hace Rails con los transactional tests. `dependency_overrides` sustituye `get_session` por la sesión del test: este es el beneficio práctico de `Depends()` del PR 1.

## Preguntas para revisar el PR 2
1. `spent_on` tiene por defecto `date.today()` **en el servidor**. Si la familia apunta un gasto a las 00:30 en España y el servidor está en UTC, ¿qué fecha se guarda? ¿Por qué el comentario dice que el cliente debería mandar la fecha?
2. `create_expense` comprueba que la categoría existe antes de insertar, aunque la clave foránea ya lo impediría. ¿Qué vería el cliente sin esa comprobación?
3. Sin `selectinload`, ¿cuántas consultas haría `GET /api/expenses` con 50 gastos?
