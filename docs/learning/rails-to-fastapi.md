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

## Conceptos del PR 6: refactor de convenciones

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

## Preguntas para revisar el PR 6
1. Si mañana queremos un endpoint con los totales de todo el año, ¿lo haríamos quitando el límite de `GET /api/expenses` o con un endpoint aparte que agregue en SQL? ¿Por qué?
2. ¿Por qué hacer `month` obligatorio no rompe el frontend, y cómo nos habríamos enterado si lo rompiera?

## Conceptos del PR 7: editar gastos (PATCH)

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `resources :expenses, only: :update` | `@router.patch("/{expense_id}")` | `update_expense` |
| `Expense.find(params[:id])` → 404 automático | `session.get(Expense, id)` + `HTTPException(404)` a mano | |
| `expense_params` con `permit` | esquema `ExpenseUpdate`, todos los campos opcionales | `app/schemas.py` |
| `expense.update(expense_params)` | `model_dump(exclude_unset=True)` + `setattr` | |
| método privado del controlador | función normal en el router | `ensure_references_exist` |

### `exclude_unset`: "no enviado" no es lo mismo que `null`
En un PATCH hay tres casos por campo, y hay que distinguirlos:
- **No lo envías**: no se toca. `exclude_unset=True` lo deja fuera del diccionario de cambios.
- **Lo envías con valor**: se actualiza.
- **Lo envías como `null`**: se borra el valor. Solo tiene sentido en `spending_type_id` ("deja este gasto sin clasificar"). En el resto de campos la columna es `NOT NULL`, y el `field_validator` `reject_null` devuelve un 422 en lugar de dejar que Postgres falle con un 500.

En Rails `permit` hace lo primero sin que lo pienses. Aquí es explícito porque Pydantic rellena con `None` los campos omitidos, y sin `exclude_unset` un PATCH con solo el concepto pondría a `NULL` todo lo demás.

### Reutilizar al segundo uso
La comprobación de "¿existe esta categoría / este tipo?" estaba escrita dos veces dentro de `create_expense`, y el PATCH la necesitaba igual. Ahora es `ensure_references_exist` y la usan los dos endpoints. Recibe `Session` y no `SessionDep`: `SessionDep` es para que FastAPI **inyecte** la sesión en un endpoint, mientras que a una función normal se la pasas tú.

### `parametrize`: una tabla de casos
`@pytest.mark.parametrize` ejecuta el mismo test con cada fila de datos. Es el equivalente a recorrer una tabla con `.each` en RSpec, pero cada fila sale como un test independiente en el informe.

### Frontend: un formulario para crear y editar
| Rails | React | En este repo |
|---|---|---|
| `_form.html.erb` compartido por `new` y `edit` | un componente con prop opcional (`expense?`) | `ExpenseForm` |
| `form_with model: @expense` (rellena los campos) | `defaultValue={expense?.concept}` | |
| modal con Turbo Frame / Stimulus | `<dialog>` nativo del navegador | `EditExpenseDialog` |

- **Reutilizar el formulario**: `ExpenseForm` sin `expense` crea y con `expense` edita. Cambian los valores iniciales, la mutación y el texto del botón; la validación y el diseño son los mismos.
- **`<dialog>` nativo**: `showModal()` ya trae el fondo oscuro, la tecla Escape, el foco atrapado dentro y la accesibilidad. No hace falta ninguna librería de modales.
- **Ref callback en lugar de `useEffect`**: para abrir el diálogo hay que llamar a `showModal()` cuando ya existe en el DOM. El `ref={(dialog) => …}` se ejecuta justo en ese momento. El padre solo decide si lo pinta (`{editing && …}`).
- **Montar y desmontar**: el formulario es no controlado, así que `defaultValue` solo se aplica al montarlo. Funciona porque al cerrar el diálogo `editing` vuelve a `null` y React lo desmonta: cada gasto que abres monta un formulario nuevo con sus valores.

## Preguntas para revisar el PR 7
1. ¿Qué pasaría si quitásemos `exclude_unset=True` y el frontend enviase solo `{"spending_type_id": 3}`?
2. ¿Por qué un `amount_cents: null` devuelve 422 y no 500? ¿Qué devolvería sin `reject_null`?
3. El PATCH hace hasta 5 consultas (gasto, categoría, tipo, update y la recarga). ¿Merece la pena optimizarlo para un formulario que se envía a mano, o sería optimizar antes de tiempo?
4. Si el diálogo estuviera siempre montado y solo cambiáramos la prop `expense`, ¿qué valores verías al abrir un segundo gasto? ¿Cómo lo arreglarías con `key`?

## Conceptos del PR 8: cuentas, login y sesiones

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `bin/rails generate authentication` (Rails 8) | lo mismo, a mano: modelo `UserSession` + cookie | `app/auth.py`, ADR 0004 |
| `has_secure_password` (bcrypt) | `pwdlib` con Argon2id | `password_hash.hash()` / `.verify()` |
| `before_action :require_authentication` | `dependencies=[Depends(current_user)]` al montar el router | `app/main.py` |
| `Current.user` | parámetro `user: CurrentUser` en el endpoint | `get_current_user` |
| `cookies.signed.permanent[:session_id]` | `response.set_cookie(..., httponly=True, secure=..., samesite="lax")` | `start_session` |
| `protect_from_forgery` | `SameSite=Lax` + middleware que compara `Origin` con `Host` | `check_origin` |
| middleware de Rack | `@app.middleware("http")` | |

### El mismo diseño que Rails 8
El generador de autenticación de Rails 8 crea una tabla `sessions` y guarda su id en una cookie firmada. Aquí es igual, con una diferencia: la cookie lleva un token aleatorio de 256 bits y en la base de datos solo guardamos su **SHA-256**. Si alguien roba una copia de la base de datos, no puede usar esos hashes como cookies. Para el token basta SHA-256 (rápido) porque es aleatorio; la contraseña necesita Argon2 (lento a propósito) porque las personas eligen contraseñas adivinables.

### Proteger "todo menos el login" en un solo sitio
En Rails pondrías `before_action` en `ApplicationController` y `allow_unauthenticated_access` en el login. Aquí se hace al revés: los routers de datos se montan con `dependencies=[Depends(current_user)]` en `main.py`, y el router de auth se monta sin ella. Un router nuevo de datos se añade a esa lista y ya está protegido.

### `APIKeyCookie`: la cookie aparece en Swagger
`current_user` no lee la cookie con `request.cookies`, sino con `APIKeyCookie(name="session")`. Funciona igual, pero además FastAPI la declara en el OpenAPI como esquema de seguridad: en `/docs` los endpoints protegidos salen con candado, y el cliente generado del frontend lo sabe.

### Middleware
`check_origin` se ejecuta en todas las peticiones, antes que cualquier endpoint, como un middleware de Rack. Si una petición que cambia datos (POST, PATCH, DELETE) trae un `Origin` de otro dominio, responde 403 sin llegar al endpoint. Por eso hubo que configurar el proxy de Vite con `changeOrigin: false`: sin eso, Vite cambiaba el `Host` a `localhost:8000` y todas las peticiones parecían de otro origen.

### Tests: `client` ya viene con sesión
En `conftest.py`, `anonymous_client` es el cliente sin cookie y `client` hace login de verdad con el usuario `user`. Los tests de gastos no han cambiado: piden `client` y ya están autenticados. Usa `https://testserver` porque la cookie es `Secure` y por HTTP no se enviaría.

### Frontend: quién soy, como un dato más del servidor
| Rails | React | En este repo |
|---|---|---|
| `if authenticated?` en el layout | `useCurrentUser()`: el usuario o `null` | `App.tsx` |
| `redirect_to new_session_path` si no hay sesión | se pinta `<AuthScreen />` en lugar de la app | |
| `rescue_from` para un 401 | interceptor de respuestas del cliente generado | `main.tsx` |

- El usuario actual es una query más de TanStack Query (`['current-user']`). Login y registro guardan el usuario que devuelve la API con `setQueryData`, sin volver a pedirlo.
- Al salir se borran de la caché todos los datos del usuario anterior (`removeQueries`), para que quien entre después no los vea ni un instante.
- Si cualquier petición devuelve 401 (sesión caducada, o cerrada en otra pestaña), el interceptor pone el usuario a `null` y la app vuelve sola a la pantalla de acceso.
- `autoComplete="current-password"` / `"new-password"` le dice al gestor de contraseñas si debe rellenar la guardada o proponer una nueva.

## Preguntas para revisar el PR 8
1. Si roban la tabla `sessions`, ¿pueden entrar como alguien? ¿Y si roban la tabla `users`?
2. ¿Por qué `authenticate` verifica un `DUMMY_HASH` cuando el email no existe, si de todas formas va a devolver 401?
3. Un formulario en `evil.example` hace POST a `/api/expenses`. ¿Qué lo para primero: `SameSite=Lax` o `check_origin`? ¿Y si el navegador fuera muy antiguo y no soportase `SameSite`?
4. El registro responde 409 si el email ya existe, lo que permite averiguar quién tiene cuenta. ¿Qué haría falta para evitarlo?
5. ¿Qué pasaría en el frontend si quitásemos el interceptor de 401 y la sesión caducase con la app abierta?

## Conceptos del PR 9: hogares

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `resources :households do resources :expenses end` | `APIRouter(prefix="/api/households/{household_id}/expenses")` | `app/routers/expenses.py` |
| `current_user.households.find(params[:household_id])` | dependencia `CurrentHousehold` | `app/auth.py` |
| `@household.expenses.find(params[:id])` | `select(Expense).where(Expense.id == …, Expense.household_id == household.id)` | `update_expense` |
| `has_many :households, through: :memberships` | `relationship(secondary="memberships")` | `User.households` |
| `add_index :expenses, [:household_id, :spent_on]` | `Index(...)` en `__table_args__` | `Expense` |
| migración con `execute "UPDATE …"` | `op.execute("…")` en la migración | `…_create_households.py` |
| FactoryBot (`create(:expense, concept: "Café")`) | fixture que devuelve una función | `make_expense` en los tests |

### Rutas anidadas y una sola puerta
En Rails harías `@household = current_user.households.find(params[:household_id])` en un `before_action`. Aquí es la dependencia `current_household`: recibe `household_id` de la URL y al usuario de `current_user`, y devuelve el hogar solo si el usuario es miembro. Cada endpoint de gastos la pide con `household: CurrentHousehold` y filtra por `household.id`. Si un endpoint nuevo se olvidase de filtrar, los tests de aislamiento son los que lo detectarían.

### 404 y no 403
Si pides el hogar de otra familia, o un gasto suyo a través de tu hogar, la respuesta es 404, como si no existiera. Con un 403 confirmarías que ese id existe. Es lo mismo que hace `current_user.households.find`, que lanza `RecordNotFound`.

### Una relación muchos a muchos sin modelo intermedio en el código
`User.households` usa `secondary="memberships"`: SQLAlchemy inserta la fila en `memberships` cuando haces `User(households=[Household(...)])`. Es como `has_many :through`. Si mañana la membresía necesita datos propios (un rol, por ejemplo), se trabaja con el modelo `Membership`, que ya existe.

### Un índice compuesto en lugar de dos
Todas las consultas filtran primero por hogar y luego por fecha. Un índice `(household_id, spent_on)` resuelve las dos cosas a la vez. El índice antiguo de `spent_on` solo ya no servía, así que lo he quitado: cada índice cuesta en cada INSERT y UPDATE.

### Migración con datos
Una columna NOT NULL nueva no se puede añadir a una tabla con filas sin decir qué valor llevan. La migración la crea como nullable, mete tus usuarios y gastos de desarrollo en un hogar "Mi hogar" con SQL, y luego la pone NOT NULL. Es el patrón de siempre en Rails, pero aquí Alembic no lo escribe solo: autogenerate solo ve el esquema.

### Fábricas en los tests
`make_expense(concept="Café")` crea un gasto en el hogar del usuario, con valores por defecto para todo lo demás. Es una fixture que devuelve una función, el equivalente de FactoryBot. Cada test escribe solo los campos que importan para lo que comprueba.

### Los tests ya no leen tu `.env`
La fixture `production_settings` (con `autouse=True`, se aplica a todos los tests) fuerza la configuración de producción. Sin ella, tu `SESSION_COOKIE_SECURE=false` local rompía el test de la cookie `Secure`. `monkeypatch` es como `allow(...).to receive` o `stub_const`: lo deshace al acabar cada test.

### Frontend: el hogar sale del usuario actual
`useHouseholdId()` lee el primer hogar de `useCurrentUser()`, que ya está en la caché. Los hooks de gastos lo usan por dentro, así que los componentes no han cambiado. El id del hogar forma parte del `queryKey` (`['expenses', householdId, month]`): si mañana cambias de hogar, la caché de cada uno va por separado.

## Preguntas para revisar el PR 9
1. ¿Qué pasaría si `update_expense` siguiera usando `session.get(Expense, expense_id)` sin filtrar por hogar? ¿Qué test lo detectaría?
2. ¿Por qué el índice es `(household_id, spent_on)` y no `(spent_on, household_id)`?
3. Si un usuario pertenece a dos hogares, ¿qué cambiaría en el backend para mostrar los dos? ¿Y en el frontend?
4. Las categorías siguen siendo globales. Si una familia quiere crear la categoría "Mascotas", ¿qué opciones hay y qué implicaría cada una?

## Conceptos del PR 10: invitaciones

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `has_secure_token :token` | `new_token()`: token aleatorio + su hash | `app/auth.py` |
| `Invitation.find_by(token:)&.destroy` | `delete(...).returning(...)`: buscar y borrar en una sola consulta | `accept_invitation` |
| tarea `rake households:create` | módulo con `if __name__ == "__main__"` + `argparse` | `uv run python -m app.invitations "Casa"` |
| `request.base_url` | `request.base_url` (igual) | `invite_to_household` |
| `params.require(:invitation_token)` | campo obligatorio en el esquema `SignUp` | 422 si falta |

### Un solo uso, garantizado por Postgres
Con "busco la invitación, compruebo que vale y luego la borro", dos registros simultáneos podrían leerla los dos antes de que ninguno la borre. `DELETE … WHERE token_hash = … AND expires_at > now() RETURNING household_id` lo hace todo en una sola sentencia: solo una de las dos peticiones consigue borrar la fila y recibe el `household_id`. La otra recibe `None` y un 400.

### Si algo falla después, la invitación sigue viva
El registro comprueba primero el email (409 si ya existe) y luego consume la invitación. Si fallase algo más tarde, no se llega al `commit`: al cerrar la sesión de SQLAlchemy se hace rollback y la fila de la invitación vuelve a estar ahí. El test `test_a_taken_email_does_not_use_up_the_invitation` lo comprueba.

### El token detrás del `#`
La parte de la URL después de `#` (el *fragment*) nunca sale del navegador: no llega al servidor ni a sus logs, ni se manda en la cabecera `Referer` a otras webs. El frontend la lee con `window.location.hash` y la envía en el cuerpo del POST de registro.

### Un comando para crear el primer hogar
Como `seed.py`, `app/invitations.py` se puede ejecutar como script. `argparse` es la librería estándar para argumentos de línea de comandos (como `OptionParser` en Ruby), y además genera el `--help`.

### Frontend: compartir desde el móvil
- `navigator.share()` abre el menú nativo de compartir del móvil (WhatsApp, Telegram…). Si no existe (por ejemplo, en un ordenador), se usa `navigator.clipboard.writeText()` para copiar.
- Las dos APIs solo funcionan en HTTPS o en `localhost`. Desde el móvil por la IP de casa no aparecen, y por eso el enlace también se muestra en un campo de texto para copiarlo a mano.
- `useState(() => readInvitation())` lee el token de la URL una sola vez, al montar la pantalla. Al registrarse, `history.replaceState` lo quita de la URL sin recargar la página.
- Si abres un enlace de invitación con la sesión ya iniciada, la app no lo ignora en silencio: muestra un aviso para salir primero. Ojo al probar: en Chrome, todas las ventanas de incógnito abiertas a la vez comparten cookies, así que una segunda ventana de incógnito ya tiene la sesión de la primera.

## Preguntas para revisar el PR 10
1. ¿Qué pasaría si `accept_invitation` hiciese un `SELECT` y luego un `session.delete()` por separado, y dos personas usasen el mismo enlace a la vez?
2. ¿Por qué el registro comprueba el email antes de consumir la invitación? ¿Qué pasaría si lo hiciera al revés?
3. Si mañana abrimos el registro a otras familias, ¿qué cambiaría en `sign_up` y en `SignUp`?
4. Cualquier miembro puede invitar. ¿Cuándo empezaría a importar tener roles (owner/member)?

## Conceptos del PR 11: nombres de usuario

Hay pocas piezas nuevas: es una columna más, con su migración y su campo en el registro.

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `validates :name, presence: true, length: { maximum: 50 }` + `strip` en un callback | tipo `PersonName` (`StringConstraints`) | `app/schemas.py` |
| `update_all("name = split_part(email, '@', 1)")` en la migración | `op.execute("UPDATE …")` | `…_add_name_to_users.py` |
| helper de specs en `spec/support/` | función normal en `conftest.py` | `sign_up()` |

### Un tipo con nombre, reutilizable
`PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]` funciona igual que `Concept`: quita espacios, no deja que quede vacío y limita la longitud. Se define una vez y se usa en cualquier esquema que reciba un nombre.

### El email es privado; el nombre, no
Los demás miembros del hogar verán tu nombre, nunca tu email. Por eso el nombre es obligatorio al registrarse y es lo que muestra la app.

### Helpers en `conftest.py`
Además de fixtures, `conftest.py` puede tener funciones normales. `sign_up(client, token, **changes)` construye un registro válido y deja cambiar cualquier campo: `sign_up(client, token, name="   ")` para probar un nombre vacío. Antes había el mismo payload copiado en dos ficheros de tests.

## Preguntas para revisar el PR 11
1. ¿Por qué la migración no puede añadir directamente `name` como NOT NULL?
2. Dos personas del hogar podrían llamarse igual. ¿Importa para el desplegable "De quién" del siguiente PR? ¿Cómo lo resolverías?

## Conceptos del PR 12: apuntado por y pagado por

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `belongs_to :created_by, class_name: "User"` | `relationship(foreign_keys=[created_by_id])` | `Expense.created_by` |
| `belongs_to :paid_by, class_name: "User", optional: true` | `Mapped["User \| None"]` + FK `ondelete="SET NULL"` | `Expense.paid_by` |
| `expense.created_by = Current.user` en el controlador | `created_by_id=user.id` en `create_expense` | |
| `includes(:paid_by, :created_by)` | `selectinload(Expense.paid_by)`, `selectinload(Expense.created_by)` | `list_expenses` |
| partial `_optional_select.html.erb` | componente `OptionalSelect` | `frontend/src/components/` |

### Dos relaciones a la misma tabla
`Expense` tiene dos claves foráneas a `users`. SQLAlchemy no puede adivinar cuál usa cada relación, así que cada una lo dice con `foreign_keys=[...]`. Es lo mismo que el `class_name` + `foreign_key` de Rails cuando el nombre de la asociación no coincide con el del modelo.

### El autor lo pone el servidor, no el cliente
`created_by_id` no está en `ExpenseCreate`, así que si un cliente lo envía, Pydantic lo ignora (por defecto descarta los campos que no conoce). El autor sale siempre de la sesión. Hay un test que lo intenta y comprueba que el autor sigue siendo el usuario que hace la petición.

### Validar que pertenece al hogar
Que `paid_by_id` sea un usuario que existe no basta: tiene que ser de **este** hogar. `ensure_references_exist` lo comprueba con un `EXISTS` sobre `memberships`. Sin eso, cualquiera podría poner como pagador a un usuario de otra familia, y su nombre aparecería en la lista.

### "Sin asignar" no es un error
Como el tipo, el pagador es opcional: se puede elegir al crear el gasto o más tarde. Mientras falte, la lista lo marca en naranja ("Sin pagador"), igual que "Sin clasificar". Así se ve de un vistazo qué gastos quedan por completar.

Al crear un gasto desde la app, el formulario ya trae seleccionado al usuario que lo apunta, porque es lo habitual. El valor por defecto está en el **frontend**, no en la API: los gastos que lleguen por otras vías (importación del banco, n8n) entran sin pagador y se ven en naranja.

### `key` para volver a montar un `<select>`
`defaultValue` solo se aplica cuando el `<select>` se monta. Si el formulario aparece antes de que lleguen los miembros, la opción con tu nombre todavía no existe, y React no vuelve a seleccionarla cuando llega. `OptionalSelect` cambia su `key` al cargar las opciones: para React es un elemento nuevo, lo vuelve a montar y entonces sí aplica el valor por defecto.

### Cambiar el diseño antes del merge
La primera versión de este PR guardaba "de quién es el gasto". Al revisarlo vimos que lo que importa es quién lo paga, por los ingresos. Como la migración aún no había llegado a `main`, la he rehecho (en desarrollo: `alembic downgrade -1`, borrar el fichero y volver a autogenerar) en lugar de añadir otra migración que renombrase la columna. Una vez mergeada, una migración ya no se toca: se añade otra.

### Extraer al segundo uso (frontend)
El desplegable "Tipo" y el nuevo "Pagado por" eran iguales: etiqueta con "(opcional)", una opción vacía y una lista que viene de la API. Ahora los dos usan `OptionalSelect`. El `""` de la opción vacía se convierte en `null` con `Number(...) || null`: `Number("")` es `0`, y ningún id es `0`.

## Preguntas para revisar el PR 12
1. ¿Qué pasaría si `ExpenseCreate` tuviera un campo `created_by_id` opcional "por si acaso"?
2. ¿Por qué `paid_by_id` tiene `ON DELETE SET NULL` y `created_by_id` no tiene `ON DELETE`? ¿Qué pasaría si `created_by_id` tuviera `CASCADE`?
3. La lista hace 5 consultas (gastos + 4 `selectinload`), da igual cuántos gastos haya. ¿Cuántas haría sin los `selectinload`, con 50 gastos?
4. Cuando lleguen los ingresos por persona, ¿cómo sería la consulta de "gastado por cada miembro este mes" en SQL?

## Conceptos del PR 13: límite de intentos

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `rate_limit to: 10, within: 3.minutes, only: :create` (Rails 8, usa la caché) | `ensure_not_throttled` + tabla `auth_failures` | `app/throttling.py` |
| `Rack::Attack` | lo mismo, a mano, en Postgres | ADR 0008 |
| `request.remote_ip` | `request.client.host` (con `--proxy-headers` detrás de un proxy) | `client_ip` |
| `head :too_many_requests` | `HTTPException(429, headers={"Retry-After": "900"})` | |

### Por qué en Postgres y no en memoria
El `rate_limit` de Rails 8 guarda los contadores en `Rails.cache` (en producción, Redis o Solid Cache). La librería típica de FastAPI, slowapi, los guarda en memoria del proceso: se pierden al reiniciar y no se comparten si arrancas varios procesos. Con una tabla en Postgres no hace falta ningún servicio más. Son dos `COUNT` con índice por login, nada que se note.

### Commit antes de lanzar el error
`record_failure` hace `commit` justo antes de que el endpoint lance el 401. Sin ese commit, la excepción haría rollback y el fallo no quedaría guardado: el contador nunca subiría.

### Tests que se comportan como producción
En producción, una petición que falla cierra su sesión sin commit y todo lo que no se había confirmado se deshace. En los tests compartimos una sesión entre peticiones, y eso no pasaba. Ahora el override de `get_session` en `conftest.py` hace commit de lo que el test ha preparado (al acabar el test se deshace todo igualmente) y rollback si la petición falla. Sin eso, el test de "un email repetido no gasta la invitación" daba un falso fallo.

### Frontend: errores con su código HTTP
El cliente generado, con `throwOnError: true`, lanza el cuerpo del error (`{detail: …}`) pero no el código HTTP. Para login y registro, `dataOrThrow` lanza un `ApiError` con el `status`. Así la pantalla distingue 401 (contraseña), 409 (email ya usado), 400 (invitación gastada) y 429 (demasiados intentos), cada uno con su mensaje en castellano.

## Preguntas para revisar el PR 13
1. ¿Por qué `ensure_not_throttled` se comprueba **antes** de verificar la contraseña? ¿Qué aprendería un atacante si lo hiciéramos después?
2. Si en producción olvidamos `--proxy-headers`, ¿qué IP verían todas las peticiones? ¿Qué pasaría con el límite de 20 por IP?
3. ¿Por qué el registro comprueba ahora la invitación antes que el email?
4. Alguien falla 5 veces con el email de tu pareja. ¿Qué ve ella al intentar entrar? ¿Cuánto dura?

## Conceptos del PR 14: seguridad en CI

| Rails | Python / React | En este repo |
|---|---|---|
| Brakeman | Ruff con las reglas `S` (las de Bandit) | `backend/pyproject.toml` |
| `bundler-audit` | `pip-audit` sobre las versiones exactas de `uv.lock` | job `backend` |
| `bundler-audit` (para JS) | `npm audit` | job `frontend` |
| — | gitleaks: busca secretos en todo el historial | job `secrets` |
| Dependabot | Dependabot (igual) | `.github/dependabot.yml` |

### Ruff `S`: Brakeman dentro del linter
Las reglas `S` buscan patrones peligrosos: SQL construido concatenando cadenas, contraseñas escritas en el código, `subprocess` con `shell=True`, `pickle`, etc. En el código de la app no ha salido nada. En los tests solo avisaba de `assert` (pytest funciona así) y de las contraseñas de prueba, que son inventadas: esas tres reglas se ignoran solo en `tests/`.

### `pip-audit` sobre lo que de verdad se instala
`uv export --frozen` saca de `uv.lock` las versiones exactas, con sus hashes, y `pip-audit --disable-pip --require-hashes` las comprueba contra la base de datos de vulnerabilidades de Python sin instalar nada. `--strict` hace fallar el CI si algo no se puede comprobar.

### `npm audit` y los `overrides`
Había 4 vulnerabilidades altas en `js-yaml`, una dependencia del generador del cliente (solo de desarrollo). `npm audit fix --force` las "arreglaba" bajando el generador a una versión anterior con cambios incompatibles. En su lugar, `"overrides": {"js-yaml": "^4.3.2"}` en `package.json` obliga a todo el árbol a usar la versión corregida, dentro de la misma versión mayor. Es como fijar una gema indirecta en el `Gemfile`. He comprobado que el generador produce exactamente el mismo cliente.

### gitleaks: el historial también cuenta
Borrar un secreto en un commit nuevo no lo quita de los anteriores, y el repo es público. Por eso el job hace checkout de **todo** el historial (`fetch-depth: 0`). Descarga una versión fija de gitleaks y comprueba su SHA-256 antes de ejecutarla: si alguien cambiase el fichero publicado, el CI fallaría en lugar de ejecutar código desconocido.

### Una vez por semana aunque no toques nada
Las vulnerabilidades se publican cualquier día. El `schedule` del workflow lo ejecuta cada lunes, así que una vulnerabilidad nueva en una dependencia pone el CI en rojo aunque nadie haya abierto un PR.

### Permisos mínimos
`permissions: contents: read` deja al token del workflow solo leer el código. Si una action de terceros estuviese comprometida, no podría escribir en el repo.

## Preguntas para revisar el PR 14
1. ¿Por qué no usar `npm audit fix --force`? ¿Qué habría cambiado?
2. Si mañana alguien sube un `.env` con una clave y la borra en el commit siguiente, ¿la detectaría gitleaks? ¿Bastaría con borrarla?
3. Un PR tuyo falla por `pip-audit` por una vulnerabilidad que no tiene nada que ver con tu cambio. ¿Qué harías?

## Conceptos del PR 22: endurecer producción

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `Rails.env.production?` | `settings.is_production` (`ENVIRONMENT`) | `app/config.py` |
| `config.force_ssl = true` (HSTS incluido) | cabecera `Strict-Transport-Security` en producción | `SECURITY_HEADERS` |
| `config.hosts << "finanzas.example.com"` (HostAuthorization) | `TrustedHostMiddleware(allowed_hosts=…)` | `app/main.py` |
| `config.action_dispatch.default_headers` | middleware `add_security_headers` | `app/main.py` |
| validar `credentials` al arrancar | `@model_validator` en `Settings` | `refuse_unsafe_production` |

### Fallar al arrancar, no en producción
`Settings` comprueba sus propios valores con un `model_validator`. En producción, si la cookie no es `Secure`, `APP_URL` no es HTTPS o no hay lista de dominios, Pydantic lanza un error y la app no llega a arrancar. Es mejor un deploy que falla en el primer segundo que una app funcionando con una configuración insegura sin que nadie lo sepa.

### Cabeceras de seguridad
Son instrucciones para el navegador:
- `Cache-Control: no-store`: no guardes esta respuesta en disco. Los datos financieros solo viven en la memoria de TanStack Query.
- `Content-Security-Policy: default-src 'none'`: esta respuesta no puede cargar nada (scripts, imágenes…). Para un JSON es lo correcto, y si un atacante consiguiera que el navegador la abriese como página, no se ejecutaría nada.
- `frame-ancestors 'none'`: ninguna web puede meterla en un `<iframe>`.
- `nosniff`: el navegador no "adivina" el tipo del contenido; si es JSON, es JSON.
- `Strict-Transport-Security`: durante dos años, este dominio solo por HTTPS. Solo en producción, porque en desarrollo usamos HTTP.

### El orden de los middlewares
En Starlette, el último middleware que se añade es el más externo: recibe la petición el primero y devuelve la respuesta el último. Por eso `add_security_headers` se declara al final: así envuelve a todos los demás, y hasta el 403 de la comprobación de `Origin` o el 400 de un `Host` desconocido llevan las cabeceras. Un test lo comprueba.

### `TrustedHostMiddleware`
La cabecera `Host` la escribe el cliente, así que se puede falsear. Nosotros la usamos para dos cosas: comparar con `Origin` (CSRF) y construir los enlaces de invitación. Con una lista de dominios permitidos, una petición con otro `Host` recibe un 400 antes de llegar a nada.

## Preguntas para revisar el PR 22
1. ¿Por qué no basta con poner `ENVIRONMENT=production` y confiar en acordarse del resto de variables?
2. Si `add_security_headers` se declarase antes que `check_origin`, ¿qué respuesta se quedaría sin cabeceras?
3. HSTS dura dos años. ¿Qué pasaría si lo activásemos en un dominio que todavía no tiene HTTPS funcionando?
4. ¿Por qué el error de configuración no debe mostrar los valores (`hide_input_in_errors`)?

## Conceptos del PR 23: la API sirve el frontend compilado

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `public/` servido por `ActionDispatch::Static` (`RAILS_SERVE_STATIC_FILES`) | `app.mount("/", StaticFiles(directory=…, html=True))` | `serve_frontend` en `app/main.py` |
| `config.public_file_server.headers` (caché de los assets) | `ASSET_HEADERS` en el middleware de cabeceras | `app/main.py` |
| `assets:precompile` con *digest* (`application-3f2a….js`) | `npm run build` de Vite (`index-EMhiBOwf.js`) | `frontend/dist/` |

### Un solo contenedor para API y frontend
En producción no hay Vite: `npm run build` genera HTML, JS y CSS estáticos en `frontend/dist`. Con `FRONTEND_DIST` apuntando ahí, FastAPI los sirve en `/`, igual que Rails sirve `public/`. Así API y frontend viajan en la misma imagen y se despliegan juntos, sin que una versión del frontend hable con otra de la API.

### `mount` va el último
Un `mount` en `/` captura todo lo que llega a él. Starlette prueba las rutas en orden, así que las de la API (todas bajo `/api/`) se declaran antes y ganan. Una ruta `/api/` que no existe sigue devolviendo el 404 en JSON de la API, no la página.

### Dos políticas de cabeceras
- **API**: `default-src 'none'` y `no-store`, como en el PR 22.
- **Página**: `default-src 'self'`, es decir, solo scripts, estilos y llamadas de nuestro propio dominio, sin código inline ni `eval`. Si alguien consiguiera inyectar un `<script>` en la página, el navegador se negaría a ejecutarlo. `index.html` lleva `no-cache` (se revalida en cada visita para ver siempre el último build).
- **Assets con hash**: caché de un año con `immutable`. Si el contenido cambia, cambia el nombre del archivo, así que nunca se sirve una versión vieja.

## Preguntas para revisar el PR 23
1. ¿Qué pasaría si `serve_frontend` se llamase antes de declarar `/api/health`?
2. ¿Por qué `index.html` no puede tener la caché de un año que tienen los assets?
3. Si un día añadimos un `<script>` inline en `index.html`, ¿qué verías en el navegador y dónde mirarías?

## Conceptos del PR 24: desplegar con Docker Compose

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `Dockerfile` que genera Rails 7.1+ (multi-stage, `assets:precompile`) | `Dockerfile` en tres etapas: Node, uv, runtime | `Dockerfile` |
| `bundle install --without development test` | `uv sync --locked --no-dev` | etapa `backend` |
| `bin/docker-entrypoint` con `db:prepare` | `alembic upgrade head && exec fastapi run` | `CMD` del `Dockerfile` |
| Puma detrás de Thruster/nginx (`config.action_dispatch.trusted_proxies`) | `fastapi run --proxy-headers --forwarded-allow-ips` | `CMD` del `Dockerfile` |
| Kamal (`kamal deploy`) | `git pull` + `docker compose … up -d --build` | `docker-compose.prod.yml` |

### Imagen en varias etapas
Cada `FROM` empieza una etapa nueva, y solo lo que se copia con `COPY --from=…` pasa a la siguiente. Node y uv se usan para construir pero no llegan a la imagen final: esta solo tiene Python, el virtualenv, el código y el `dist` del frontend (287 MB). Es lo mismo que hace el `Dockerfile` de Rails con `assets:precompile`.

### `exec` en el `CMD`
`sh -c "alembic upgrade head && exec fastapi run …"`: con `exec`, el servidor sustituye al `sh` y pasa a ser el proceso 1 del contenedor. Así recibe directamente la señal de parada de Docker y se cierra limpio, sin esperar los 10 segundos tras los que Docker lo mataría.

### La IP real del cliente
Entre el navegador y la app está Caddy, así que la conexión siempre llega desde la IP de Caddy. Caddy apunta la IP original en la cabecera `X-Forwarded-For`, y `--proxy-headers` hace que uvicorn la use como `request.client.host`. Sin eso, el límite de intentos por IP del PR 13 vería a toda la familia como una sola IP. Confiar en cualquier remitente (`'*'`) solo es seguro porque el contenedor no publica puertos: nadie más que Caddy puede hablarle.

### Redes de Docker y alias
Cada compose crea su red `default`, donde los servicios se encuentran por nombre (`db`, `web`). La red `proxy` es externa y compartida con Caddy; dentro de ella dos apps tienen un servicio `web`, así que cada una entra con un alias propio (`family-finances`). La base de datos solo está en la red `default`: Caddy no puede verla.

## Preguntas para revisar el PR 24
1. Si una migración falla al arrancar, ¿qué pasa con la versión anterior de la app? ¿Y con los datos?
2. ¿Qué pasaría con el límite de intentos si quitásemos `--proxy-headers`?
3. ¿Por qué `ENVIRONMENT=production` está escrito en el compose en vez de leerse del `.env.production`?
4. ¿Qué tendría que cambiar si un día publicásemos el puerto 8000 del contenedor?

## Conceptos del PR 25: backups

| Rails | Aquí | En este repo |
|---|---|---|
| `whenever` / cron en el servidor | timer de systemd (`OnCalendar`, `Persistent=true`) | `family-finances-backup.timer` |
| `pg_dump` en una tarea `rake db:backup` | `pg_dump` dentro del contenedor `db` con `docker compose exec -T` | `backup.sh` |
| cron en el Mac | agente de `launchd` (`StartCalendarInterval`) | `com.family-finances.backup-pull.plist` |

### Timer de systemd frente a cron
Un timer es un "cron" gestionado por systemd. Con `Persistent=true`, si el servidor estaba apagado a las 03:15, el backup se hace al arrancar. Los logs quedan en `journalctl -u family-finances-backup`, y `systemctl list-timers` muestra cuándo fue la última y cuándo será la próxima.

### Un backup que nadie ha restaurado no es un backup
El riesgo no es solo perder datos, sino descubrir el día que los necesitas que la copia está vacía o no se puede cargar. Por eso: el dump se escribe en `.tmp` y solo se renombra si termina bien; el Mac avisa si la última copia tiene más de 48 horas; y la primera restauración se ensaya en una base de datos aparte.

### `-T` en `docker compose exec`
Sin `-T`, Docker reserva una terminal (TTY) para el comando. Con una TTY, la salida de `pg_dump` se mezclaría con códigos de terminal y el gzip quedaría corrupto. Con `-T`, la salida es un flujo limpio que se puede encadenar con `|`.

## Preguntas para revisar el PR 25
1. Si `pg_dump` falla a mitad, ¿qué archivo queda en `/var/backups/family-finances`? ¿Y si no usásemos el `.tmp`?
2. El Mac estuvo apagado una semana de vacaciones. ¿Qué copias tendrás al volver? ¿Y en el servidor?
3. ¿Qué datos perderías si el servidor muere a las 03:10? ¿Y a las 03:20?

## Conceptos del PR 26: tokens de API con scopes

| Rails | Python / FastAPI | En este repo |
|---|---|---|
| `has_secure_token` | `secrets.token_urlsafe(32)` con prefijo `ff_`, guardado como SHA-256 | `new_api_token` en `app/auth.py` |
| `authenticate_or_request_with_http_token` | `HTTPBearer(auto_error=False)` | `bearer` en `app/auth.py` |
| scopes de Doorkeeper (`doorkeeper_authorize! :write`) | `Security(current_user, scopes=["expenses:write"])` + `SecurityScopes` | `ExpensesWriter`, `WritableHousehold` |
| `before_action` en un controlador | `dependencies=[Security(…)]` al incluir el router | `app/main.py` |
| `ActiveRecord` con columna `array: true` | `ARRAY(String)` de SQLAlchemy (Postgres) | `ApiToken.scopes` |

### `Depends` frente a `Security`
`Security` es un `Depends` que además declara scopes. FastAPI los va acumulando por la cadena de dependencias: si un endpoint pide `WritableHousehold`, la dependencia `current_household` hereda el scope `expenses:write` y se lo pasa a `current_user`, que lo recibe en `security_scopes`. Así el endpoint solo dice qué necesita, y la comprobación vive en un único sitio.

### Denegar por defecto
`current_user` deja pasar a un token solo si el endpoint ha pedido algún scope. Si no ha pedido ninguno, responde 403. Es la misma idea que el `verify_authorized` de Pundit: lo que nadie ha autorizado de forma explícita queda cerrado. Un endpoint nuevo es "solo navegador" hasta que alguien decida abrirlo a los tokens.

### Una consulta por petición
Comprobar quién llama (cookie o token) es una dependencia aparte, sin scopes. FastAPI cachea cada dependencia durante la petición, así que aunque `current_user` se llame varias veces con scopes distintos, la base de datos se consulta una sola vez.

### 401 frente a 403
- **401**: no sé quién eres (token desconocido o revocado). Lleva `WWW-Authenticate: Bearer`.
- **403**: sé quién eres, pero este token no puede hacer esto. Lleva `error="insufficient_scope"` y los scopes que harían falta (RFC 6750).

## Preguntas para revisar el PR 26
1. Si mañana añades `DELETE /api/households/{id}/expenses/{id}` usando `CurrentHousehold`, ¿podría usarlo un token con `expenses:write`? ¿Qué cambiarías para permitirlo?
2. Alguien roba un backup de la base de datos. ¿Puede usar los tokens que hay en `api_tokens`? ¿Por qué basta con SHA-256 y no hace falta Argon2 como en las contraseñas?
3. ¿Por qué `last_used_at` solo se actualiza una vez por minuto?
4. Si una petición trae a la vez cookie y token, ¿cuál gana? ¿Por qué tiene sentido?

## Conceptos del PR 27: pantalla de tokens

| Rails | React / TanStack Query | En este repo |
|---|---|---|
| una sección plegable con Stimulus | `<details>` / `<summary>` nativos, sin JavaScript propio | `ApiTokensSection` |
| cargar un frame de Turbo solo al abrirlo (`loading="lazy"`) | `useQuery({ enabled })` | `useApiTokens(enabled)` |
| `flash.now[:token]` que solo se muestra una vez | el `data` de la mutación, que se olvida con `reset()` | `NewToken` |
| `data-turbo-confirm` | `window.confirm` antes de `mutate` | `TokenRow` |

### Cargar solo cuando hace falta
La lista de tokens no se pide al abrir la app: casi nunca se mira. `TokensPanel` solo se monta cuando el `<details>` está abierto, y es entonces cuando `useApiTokens` hace la petición. Si lo cierras y lo vuelves a abrir, TanStack Query devuelve lo que ya tenía en caché.

### Un secreto que solo vive en memoria
El token completo llega únicamente en la respuesta de `POST /api/tokens`. No se guarda en el estado de la app ni en la caché de la lista: se queda en el `data` de esa mutación hasta que pulsas «Hecho» (`create.reset()`). A partir de ahí no hay forma de recuperarlo, ni para la app ni para el servidor.

## Preguntas para revisar el PR 27
1. ¿Qué peticiones hace la app al cargar la página principal? ¿Ha cambiado algo con este PR?
2. Si recargas la página justo después de crear un token, sin copiarlo, ¿puedes recuperarlo? ¿Qué harías entonces?
3. ¿Por qué después de crear o revocar un token basta con `invalidateQueries` en vez de modificar la lista a mano?

## Conceptos del PR 28: Ajustes en un diálogo

| Rails | React | En este repo |
|---|---|---|
| un partial compartido (`_modal.html.erb`) | un componente compartido con `children` | `Dialog` |
| `yield` dentro del partial | la prop `children: ReactNode` | `Dialog`, `Section` |

### Extraer cuando algo se repite
`EditExpenseDialog` ya resolvía cómo abrir un `<dialog>` nativo, cerrarlo con Escape o tocando fuera y avisar al padre. Ajustes necesitaba lo mismo, así que esa parte pasa a `Dialog` y los dos lo usan; cada uno solo decide su contenido y su aspecto (`className`).

### Un diálogo en vez de una página
Sin router, una "pantalla" de ajustes como estado de `App` tendría un problema: el botón «atrás» del móvil saldría de la app. Un `<dialog>` modal nativo lo evita: Chrome en Android lo cierra con «atrás», como se espera de una pantalla. Cuando lleguen los informes meteremos un router, y Ajustes pasará a ser una ruta.

## Preguntas para revisar el PR 28
1. ¿Por qué `SettingsDialog` se monta solo cuando `settingsOpen` es `true`, en vez de estar siempre en la página y ocultarse con CSS?
2. Si cierras sesión desde Ajustes, ¿quién cierra el diálogo?

## Conceptos del PR 29: arrancar más rápido

| Rails | Python | En este repo |
|---|---|---|
| `bootsnap` (cachea la carga de código) | bytecode precompilado (`python -m compileall`) | `Dockerfile` |
| `bin/docker-entrypoint` que hace `db:prepare` y luego `exec "$@"` | un solo script de Python: Alembic por código y `uvicorn.run` | `app/serve.py` |

### Medir antes de arreglar
La sospecha inicial era que el contenedor viejo no se cerraba (10 s esperando a Docker). Medido en el servidor: se cierra en 1,5 s. El tiempo de verdad se iba en **importar la app**: unos 5 s en un servidor de 1 CPU con swap, y se pagaba dos veces, una para Alembic y otra para la CLI de `fastapi`, que además carga sus propias librerías. `python -X importtime -c "import app.main"` enseña qué módulo cuesta cuánto.

### Un proceso en vez de dos
`app/serve.py` llama a `alembic.command.upgrade` como una función y después a `uvicorn.run`. Lo que Alembic ya importó (SQLAlchemy, los modelos, la configuración) sigue cargado cuando arranca el servidor. Además, como `python -m app.serve` es el proceso 1 del contenedor, ya no hace falta el truco del `exec` en un `sh -c`.

### `.pyc` en la imagen
Python guarda el bytecode de cada módulo en `__pycache__` para no recompilarlo. El contenedor corre con un usuario sin permiso para escribir en `/app`, así que no podía guardarlo y recompilaba la app en cada arranque. Ahora se compila una vez al construir la imagen.

## Preguntas para revisar el PR 29
1. Si una migración falla, ¿qué hace `app/serve.py`? ¿Llega a arrancar uvicorn?
2. ¿Por qué no basta con medir en tu Mac para saber cuánto tarda en arrancar en el servidor?

## Conceptos del PR 32: eliminar un gasto

| Rails | FastAPI / SQLAlchemy | En este repo |
|---|---|---|
| `def destroy` + `head :no_content` | `@router.delete(..., status_code=204)` que devuelve `None` | `delete_expense` |
| `Expense.where(id:, household_id:).delete_all` | `session.execute(delete(Expense).where(...))` | `delete_expense` |
| `@expense.destroy` (carga el registro y ejecuta callbacks) | `session.delete(objeto)` | no se usa aquí |

### Un solo `DELETE`, sin cargar el gasto
En vez de buscar el gasto y luego borrarlo (dos consultas), se lanza directamente `DELETE … WHERE id = … AND household_id = …`. Si `rowcount` es 0, o no existe o es de otro hogar: en los dos casos, 404. Es el mismo patrón que ya usaba revocar un token. El precio es el mismo que con `delete_all` en Rails: no hay callbacks. Aquí no los necesitamos.

### Borrado definitivo
No hay papelera (`deleted_at`): obligaría a filtrar los borrados en cada consulta. Si alguien se equivoca, están las copias diarias (ADR 0011). Por eso el frontend pide confirmación en dos pasos dentro del propio diálogo.

### Objetos "caducados" tras un `commit`
En los tests, la sesión del test y la de la petición son la misma. Tras el `commit`, SQLAlchemy marca los objetos como caducados y, al leer `coffee.id`, intenta recargarlo… de una fila que ya no existe (`ObjectDeletedError`). Por eso el test guarda el id antes de la petición. En Rails, `@expense.id` sigue disponible después del `destroy` porque ActiveRecord no recarga solo.

## Preguntas para revisar el PR 32
1. ¿Por qué borrar un gasto de otro hogar responde 404 y no 403?
2. Un token con solo `expenses:read` intenta borrar: ¿qué responde la API y en qué punto del código se decide?
3. Después de borrar, ¿cómo se entera la lista del mes de que el gasto ya no está?

## Conceptos del PR 33: ingresos

| Rails | FastAPI / React | En este repo |
|---|---|---|
| un *concern* o un módulo con métodos compartidos entre controladores | un módulo de funciones y tipos que importan los dos routers | `app/routers/common.py` |
| un `scope :in_month` reutilizable | `month_bounds(month)` + el tipo `Month` para el parámetro | `common.py` |
| un partial de formulario (`_amount_field.html.erb`) | un componente pequeño con props | `AmountField` |
| `before_action` que solo deja pasar sesiones | el router se registra con `Depends(current_user)` sin scopes | `main.py` |

### Dos tablas, código compartido
Ingresos y gastos se parecen, pero no son lo mismo (el ADR 0013 lo explica). Lo que comparten no va al esquema sino al código: el parámetro `month`, cómo se convierte en un rango de fechas y la comprobación de que el pagador o el receptor es del hogar. En Rails lo meterías en un concern; aquí son funciones normales en `common.py`.

### Un alias de tipo con validación
`AmountCents = Annotated[int, Field(gt=0, ...)]` junta el tipo y la regla. `ExpenseCreate` e `IncomeCreate` lo usan, así que "positivo y en céntimos" está escrito una sola vez, igual que ya pasaba con `Concept`.

### El resumen no pide nada nuevo
`MonthSummary` llama a `useIncomes(month)` y `useExpenses(month)`, los mismos hooks que usan las listas de debajo. TanStack Query reconoce la misma `queryKey` y sirve los datos de la caché: tres componentes, dos peticiones. El total se calcula en cada render a partir de esos datos, sin guardarlo en un estado aparte.

### Un interruptor con `aria-pressed`
El selector Gasto | Ingreso son dos botones con `aria-pressed`. Así el lector de pantalla anuncia cuál está activo, y Tailwind lo pinta con la variante `aria-pressed:`, sin clases condicionales en JavaScript.

## Preguntas para revisar el PR 33
1. Si un día quieres que n8n meta las nóminas, ¿qué tendrías que cambiar para que un token pueda crear ingresos?
2. ¿Qué pasa con los ingresos de alguien si se borra su usuario? ¿Y si se borra el hogar?
3. Al cambiar de Gasto a Ingreso a mitad de escribir, ¿qué pasa con lo que habías tecleado? ¿Te parece bien?
