"""Express (TypeScript) framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Express / TypeScript)
- Layer as Router → Controller → Service → Repository. Routers own \
route definitions; controllers parse requests; services contain \
business logic; repositories handle data access.
- Use middleware for cross-cutting concerns: error handling, auth, \
logging, CORS, request validation. Register with `app.use()`.
- Validate request input with express-validator or zod middleware. \
Never trust `req.body`, `req.params`, or `req.query` without validation.
- Centralize error handling in a final error middleware \
`(err, req, res, next)`. Never send raw error messages to clients.
- Use TypeScript strict mode (`"strict": true` in tsconfig.json). \
Type all request/response bodies with interfaces.
- Use async/await with proper error propagation. Wrap async route \
handlers to catch rejected promises (or use express-async-errors).
- Environment config via dotenv. Load once at startup, validate \
required vars, and export a typed config object.\
""",
    "architecture": """\
# Architecture — Express (TypeScript)

## Directory Layout
```
src/
  app.ts               # Express app setup (middleware, routes)
  server.ts            # Entry point (listen, graceful shutdown)
  routes/
    index.ts           # Route aggregator
    user.routes.ts     # User resource routes
  controllers/
    user.controller.ts # Request parsing, response formatting
  services/
    user.service.ts    # Business logic
  repositories/
    user.repo.ts       # Database access (Prisma, TypeORM, Knex)
  middleware/
    auth.ts            # JWT / session authentication
    validate.ts        # Request validation middleware
    errorHandler.ts    # Centralized error handler
  models/
    user.model.ts      # Type definitions / DB models
  types/
    index.ts           # Shared TypeScript types
  config/
    index.ts           # Environment config with validation
src/__tests__/
  controllers/         # Controller tests
  services/            # Service unit tests
  integration/         # Full request cycle tests
```

## Key Patterns
- **Router modules**: each resource gets its own router file. Mount \
all routers in `routes/index.ts`.
- **Middleware pipeline**: request flows through global middleware, \
then route-specific middleware, then the handler.
- **Error middleware**: must be registered last. Catches all errors \
and returns consistent JSON error responses.
- **Dependency injection**: pass services to controllers via factory \
functions or a DI container (tsyringe, awilix).
- **Graceful shutdown**: handle SIGTERM, close DB connections, drain \
active requests before exiting.
- **TypeScript strict**: `noUncheckedIndexedAccess`, `noImplicitAny`, \
`strictNullChecks` all enabled.\
""",
    "conventions": """\
# Conventions — Express (TypeScript)

## Naming
- Files: kebab-case (`user.controller.ts`, `auth.middleware.ts`).
- Classes/Interfaces: PascalCase (`UserService`, `CreateUserDto`).
- Functions/variables: camelCase (`getUserById`, `isAuthenticated`).
- Route files: `resource.routes.ts` (e.g., `user.routes.ts`).

## Controller Guidelines
- One controller per resource. Export handler functions or a class.
- Parse input → validate → call service → format response.
- Use typed request/response generics: `Request<Params, ResBody, ReqBody>`.
- Return consistent response shapes: `{ data, error, meta }`.

## Service Guidelines
- Services are framework-agnostic — no Express types (Request, Response).
- Throw custom error classes (`NotFoundError`, `ValidationError`) — \
let error middleware handle HTTP mapping.
- Return typed results, not raw database objects.

## Error Handling
- Define error classes extending a base `AppError` with `statusCode`.
- Express error middleware maps `AppError` subclasses to HTTP responses.
- Log 5xx errors at ERROR level; 4xx at WARN or DEBUG.

## Code Style
- ESLint + Prettier for formatting and linting.
- Prefer `const` over `let`. Never use `var`.
- Use `interface` for object shapes, `type` for unions and intersections.
- Import paths: use path aliases (`@/services/...`) via tsconfig paths.\
""",
    "testing": """\
# Testing — Express (TypeScript)

## Stack
- **Framework**: Jest or Vitest with TypeScript support.
- **HTTP testing**: Supertest for endpoint integration tests.
- **Mocking**: jest.mock() or vi.mock() for service dependencies.
- **Database**: test database with transactions or in-memory SQLite.

## Principles
- Test through the HTTP layer with Supertest for integration tests. \
Validates routing, middleware, validation, and serialization.
- Unit test services in isolation with mocked repositories.
- Mock external services (APIs, email) at the boundary.
- Test both success and error paths, including validation failures.

## File Layout
```
src/__tests__/
  controllers/
    user.controller.test.ts   # Supertest endpoint tests
  services/
    user.service.test.ts      # Service unit tests
  middleware/
    auth.test.ts              # Middleware unit tests
  integration/
    user.flow.test.ts         # Full flow tests
```

## Commands
- `npm test` — run all tests.
- `npm test -- --watch` — watch mode.
- `npm test -- --coverage` — with coverage report.
- `npm test -- --testPathPattern=user` — run matching tests.\
""",
    "deployment": """\
# Deployment — Express (TypeScript)

## Build
- `npm run build` compiles TypeScript to JavaScript in `dist/`.
- `tsc --noEmit` for type checking without emitting files.
- Use `tsconfig.build.json` that excludes test files.

## Docker
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

## Production
- Use PM2 for process management: `pm2 start dist/server.js -i max`.
- Enable clustering for multi-core utilization.
- Set `NODE_ENV=production` for optimized behavior.
- Use helmet middleware for security headers.

## Environment
- `PORT` — HTTP port (default 3000).
- `NODE_ENV` — environment (production, development, test).
- `DATABASE_URL` — database connection string.
- `JWT_SECRET` — JWT signing key.
- `LOG_LEVEL` — logging verbosity (info, debug, error).\
""",
}
