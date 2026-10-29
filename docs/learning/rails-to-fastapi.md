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

## Conceptos del PR 3: el frontend en React

| Rails | React | En este repo |
|---|---|---|
| vista / partial | componente (una función que devuelve JSX) | `src/components/` |
| locals de un partial | props | `<ExpenseList month={month} />` |
| `@expenses = Expense.all` en el controlador | `useQuery` (estado del servidor) | `src/api/queries.ts` |
| `form_with` + `create` + redirect | `useMutation` + invalidar la caché | `useCreateExpense` |
| helpers (`number_to_currency`) | funciones puras en `lib/` | `src/lib/money.ts` |
| cliente HTTP a mano | cliente generado desde el OpenAPI | `src/api/generated/` |

### Un componente es una función que se vuelve a ejecutar
`ExpenseList` es una función. React la llama cada vez que cambia algo de lo que depende (sus props o los datos de su query) y actualiza en el DOM solo lo que ha cambiado. Por eso el total del mes se **calcula** en cada render (`reduce`) en lugar de guardarse aparte: si lo guardaras como estado, tendrías que mantenerlo sincronizado a mano. Regla: **si algo se puede calcular a partir de otro dato, no es estado.**

### Dos tipos de estado
- **Estado del servidor** (los gastos, las categorías): vive en la API, y en el navegador hay una copia en caché. Lo gestiona **TanStack Query**: pide los datos, los guarda en caché por `queryKey`, los vuelve a pedir cuando hace falta y te da `isPending`, `isError` y `data`. Nunca lo copies a un `useState`.
- **Estado del cliente** (el mes elegido, el error del importe): solo existe en la pantalla. Se guarda con `useState`.

Es el concepto más importante del frontend. Casi todos los bugs típicos de React vienen de mezclar los dos.

### `queryKey` e invalidación
`['expenses', '2026-10']` identifica una lista en caché. Al crear un gasto, `invalidateQueries({ queryKey: ['expenses'] })` marca como caducadas **todas** las listas de gastos, sea cual sea su mes, y la que está en pantalla se vuelve a pedir sola. Es el equivalente a `redirect_to expenses_path` tras un create, pero sin recargar la página.

### Por qué no hay ningún `useEffect`
La forma antigua de cargar datos era `useEffect(() => { fetch(...).then(setExpenses) }, [])`. Aparecían condiciones de carrera, no había caché y había que gestionar a mano los estados de carga y de error. `useQuery` resuelve todo eso. Si en un PR ves un `useEffect`, pregunta por qué.

### Formulario no controlado
Los inputs del formulario no están atados a ningún estado de React. Al enviar, `new FormData(form)` lee lo que el usuario ha escrito, como en un formulario HTML de toda la vida. Tiene menos código y menos renders. Cuando los formularios crezcan (edición o validación compleja), pasaremos a `react-hook-form` + `zod`.

### El cliente generado
`npm run gen:api` pide el OpenAPI al backend y genera `listExpenses()`, `createExpense()` y los tipos `ExpenseRead` y `ExpenseCreate`. Si en el backend cambias `amount_cents` y regeneras, TypeScript marca cada sitio del frontend que se ha roto. **El backend es la única fuente de verdad de los tipos.** Los nombres limpios salen de `operation_id` en `backend/app/main.py`.

### El dinero, solo en los bordes
El usuario escribe "12,50". `parseAmountToCents` lo convierte en `1250` trabajando con los dígitos del texto, nunca con floats, y `formatCents` lo vuelve a mostrar como "12,50 €". En medio, todo son enteros (ADR 0002).

## Preguntas para revisar el PR 3
1. El formulario manda `spent_on` con `todayISO()` del navegador. ¿Resuelve esto la pregunta 1 del PR 2? ¿Por qué `new Date().toISOString().slice(0, 10)` sería un error?
2. Si guardas un gasto con fecha de septiembre mientras ves octubre, ¿se actualiza la lista de septiembre? ¿Cuándo se vuelve a pedir?
3. En `ExpenseList`, ¿por qué el `key` de cada `<li>` es `expense.id` y no la posición en la lista?

## Conceptos del PR 4: tipo de gasto (una relación opcional)

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `belongs_to :spending_type, optional: true` | `Mapped[int \| None]` + `Mapped[SpendingType \| None]` | `Expense.spending_type` |
| segunda migración (`add_reference`) | `alembic revision --autogenerate`, encadenada con `down_revision` | `migrations/versions/` |
| `params.permit(:spending_type_id)` opcional | `spending_type_id: int \| None = None` | `ExpenseCreate` |
| `rails db:rollback` | `alembic downgrade -1` | |

### Opcional en tres capas
En Rails basta con `optional: true`. Aquí hay que decirlo en cada capa, y cada una significa una cosa distinta:
- **Modelo**: `Mapped[int | None]` hace que la columna admita NULL.
- **Esquema de entrada**: `int | None = None`. El `= None` es lo que hace que el campo se pueda **omitir** en el JSON. Sin él, sería obligatorio enviarlo, aunque fuera con `null`.
- **Esquema de salida**: `SpendingTypeRead | None`, **sin** valor por defecto, porque la respuesta siempre incluye la clave: con el objeto, o con `null`.

### Las migraciones se encadenan
Cada migración apunta a la anterior con `down_revision`. Es el equivalente al timestamp del nombre de fichero en Rails, pero explícito: Alembic recorre la cadena para saber qué falta por aplicar.

### Revisar la migración autogenerada (otra vez)
Alembic creó la clave foránea **sin nombre** (`None`), y su propio comentario avisaba de que el `downgrade` fallaría. Le he puesto el nombre a mano y he probado `upgrade`, `downgrade -1` y `upgrade` otra vez. Rails pone nombre a las claves foráneas automáticamente; Alembic no, salvo que configures una *naming convention* en `Base.metadata`.

## Preguntas para revisar el PR 4
1. ¿Qué pasaría si `ExpenseCreate` tuviera `spending_type_id: int | None` sin el `= None`? ¿Seguiría funcionando el frontend actual, que no envía ese campo?
2. `list_spending_types` ordena por `id` y no por nombre, como hacen las categorías. ¿Qué pasa con ese orden si mañana se añade un sexto tipo que debería ir entre "Gastos básicos" y "Educación"?
3. ¿Merece la pena configurar una naming convention en `Base.metadata` para no tener que poner nombres a mano en cada migración?

## Conceptos del PR 5: el tipo de gasto en el frontend

No hay piezas nuevas: `useSpendingTypes` es igual que `useCategories`. Lo interesante es cómo viaja un campo **opcional** desde un `<select>`.

### `""` no es `null`
Un `<select>` siempre tiene valor: la opción "Sin clasificar" manda la cadena vacía `""`. Si la enviáramos tal cual, Pydantic intentaría convertir `""` en un `int` y devolvería un 422. Por eso el formulario traduce `""` a `null` antes de llamar a la API. En Rails pasa lo mismo, pero ActiveRecord lo disimula: convierte `""` en `nil` al asignarlo a una columna integer.

### TypeScript avisa si te olvidas
Al regenerar el cliente en el PR 4, `ExpenseRead.spending_type` pasó a ser `SpendingTypeRead | null`. Si escribes `expense.spending_type.name` sin comprobar antes que no es `null`, `tsc` da error. Es lo que en Ruby sería un `NoMethodError` en producción, aquí detectado al compilar.

## Preguntas para revisar el PR 5
1. ¿Qué pasaría si quitásemos el `spendingTypeId ? … : null` y mandásemos `Number(data.get('spending_type_id'))`? (pista: `Number("")`)
2. En la lista, los gastos sin tipo no muestran nada. ¿Preferirías ver "Sin clasificar" para detectarlos de un vistazo, ahora que vamos a poder editarlos?

## Refactor de convenciones

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| nombres de FK automáticos (`fk_rails_…`) | `naming_convention` en `Base.metadata` | `app/models.py` |
| `.rubocop.yml` con más cops (`rubocop-rails`, `rubocop-rspec`) | más reglas en `[tool.ruff.lint] select` | `backend/pyproject.toml` |

### Naming convention
Sin convención, SQLAlchemy deja las foreign keys sin nombre y Postgres les pone uno al crearlas. Alembic no conoce ese nombre, así que el `downgrade` no sabe qué borrar (es lo que nos pasó en la migración de los tipos de gasto). Con la convención, SQLAlchemy decide el nombre y lo escribe en cada migración autogenerada. La he configurado con **los mismos nombres que pone Postgres** (`expenses_category_id_fkey`, `categories_name_key`…), así que la base de datos actual ya cumple y no hace falta ninguna migración. Lo he comprobado comparando los 10 nombres uno a uno.

### Listas siempre acotadas
`GET /api/expenses` ahora exige `?month=`. Antes, sin el mes, devolvía todos los gastos de la historia: con pocos datos no se nota, pero el tiempo de respuesta y la memoria crecen sin límite. Cuando haya una lista sin límite natural, la acotaremos con paginación.

### Reglas nuevas de Ruff
- `FAST`: convenciones de FastAPI. Detectó que `/api/health` declaraba el modelo dos veces: con `response_model=Health` y con `-> Health`. Cuando el tipo de retorno ya es el esquema, sobra el `response_model`. En los demás endpoints sí hace falta, porque devuelven un modelo SQLAlchemy y el esquema de salida es otro.
- `PT`: buenas prácticas de pytest. `PERF`: antipatrones de rendimiento en bucles. `RUF`: reglas propias de Ruff.

## Preguntas para revisar el refactor
1. Si mañana queremos un endpoint con los totales de todo el año, ¿lo haríamos quitando el límite de `GET /api/expenses` o con un endpoint aparte que agregue en SQL? ¿Por qué?
2. ¿Por qué hacer `month` obligatorio no rompe el frontend, y cómo nos habríamos enterado si lo rompiera?
