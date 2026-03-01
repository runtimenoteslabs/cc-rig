"""ASP.NET Core framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (C# / ASP.NET Core)
- Use [ApiController] attribute on controllers. Return ActionResult<T> \
or IActionResult for explicit HTTP status codes.
- Register services in Program.cs with IServiceCollection. Use \
constructor injection everywhere — never use service locator pattern.
- Use the Options pattern (IOptions<T>) for configuration. Bind config \
sections to POCO classes, never read IConfiguration directly in services.
- Validate input with DataAnnotations ([Required], [StringLength]) or \
FluentValidation. Return 400 with ProblemDetails for validation failures.
- Use DTOs for API request/response bodies. Never expose EF Core \
entities directly in API responses.
- Enable nullable reference types (NRTs) project-wide. Treat all \
nullable warnings as errors.
- Use async/await consistently. Suffix async methods with Async. \
Never use .Result or .Wait() — it causes deadlocks.\
""",
    "architecture": """\
# Architecture — C# / ASP.NET Core

## Directory Layout
```
src/
  MyApp.Api/
    Controllers/
      UsersController.cs      # [ApiController] — HTTP endpoints
    Program.cs                 # Host builder, DI registration, middleware
    appsettings.json           # Base configuration
    appsettings.Development.json
    appsettings.Production.json
  MyApp.Core/
    Services/
      UserService.cs           # Business logic
    Interfaces/
      IUserService.cs          # Service contracts
    Models/
      User.cs                  # Domain model
    DTOs/
      UserRequest.cs           # Request DTO with validation
      UserResponse.cs          # Response DTO
  MyApp.Infrastructure/
    Data/
      AppDbContext.cs           # EF Core DbContext
      Migrations/              # EF Core migrations
    Repositories/
      UserRepository.cs        # Data access
tests/
  MyApp.Tests/
    Controllers/
      UsersControllerTests.cs  # WebApplicationFactory tests
    Services/
      UserServiceTests.cs      # Unit tests with Moq
    Integration/
      UserFlowTests.cs         # Full integration tests
```

## Key Patterns
- **Clean Architecture**: Api → Core ← Infrastructure. Core has no \
framework dependencies.
- **Middleware pipeline**: UseRouting → UseAuthentication → \
UseAuthorization → MapControllers. Order matters.
- **EF Core**: code-first migrations. Use `dotnet ef migrations add` \
for schema changes. Never edit migration files after applying.
- **Dependency injection**: register with Scoped (per-request), \
Transient (per-resolve), or Singleton lifetime.
- **Error handling**: global exception middleware + ProblemDetails \
for consistent API error responses.\
""",
    "conventions": """\
# Conventions — C# / ASP.NET Core

## Naming
- Classes, methods, properties: PascalCase (`UserController`, \
`GetByIdAsync`, `FirstName`).
- Parameters, local variables: camelCase (`userId`, `userService`).
- Interfaces: I-prefix (`IUserService`, `IUserRepository`).
- Private fields: _camelCase (`_userService`, `_logger`).
- Async methods: Async suffix (`GetUserAsync`, `CreateAsync`).

## Controller Guidelines
- One resource per controller. Use [Route("api/[controller]")].
- Use [HttpGet], [HttpPost], [HttpPut], [HttpDelete] attributes.
- Return ActionResult<T> for type-safe responses.
- Use [FromRoute], [FromBody], [FromQuery] for explicit binding.
- Keep controllers thin — delegate to services immediately.

## Service Guidelines
- Define service interfaces in Core project.
- Implement in Infrastructure or Api project.
- Throw custom exceptions — let middleware handle HTTP mapping.
- Return domain objects, not HTTP-specific types.

## Code Style
- Follow Microsoft C# coding conventions.
- Use file-scoped namespaces (C# 10+).
- Use primary constructors (C# 12+) or explicit constructors.
- Prefer pattern matching and switch expressions.
- Use `dotnet format` for consistent formatting.\
""",
    "testing": """\
# Testing — C# / ASP.NET Core

## Stack
- **Framework**: xUnit ([Fact], [Theory], [InlineData]).
- **Integration**: WebApplicationFactory<Program> for in-memory \
test server.
- **Mocking**: Moq (Mock<T>, Setup, Verify) or NSubstitute.
- **Assertions**: FluentAssertions (Should(), BeEquivalentTo()) \
preferred over xUnit Assert.

## Principles
- Use WebApplicationFactory<Program> for integration tests — spins \
up the full middleware pipeline in-memory.
- Override services with WithWebHostBuilder for test doubles.
- Use EF Core InMemory provider or Testcontainers for database tests.
- Test both success and error paths. Verify ProblemDetails format.

## File Layout
```
tests/
  MyApp.Tests/
    Controllers/
      UsersControllerTests.cs  # WebApplicationFactory integration
    Services/
      UserServiceTests.cs      # Pure unit tests with Moq
    Repositories/
      UserRepositoryTests.cs   # EF Core InMemory tests
    Helpers/
      TestWebApplicationFactory.cs  # Custom factory with overrides
```

## Commands
- `dotnet test` — run all tests.
- `dotnet test --filter FullyQualifiedName~UserService` — filter tests.
- `dotnet test --filter Category=Integration` — run by category.
- `dotnet test --logger "console;verbosity=detailed"` — verbose output.
- `dotnet test /p:CollectCoverage=true` — with coverage.\
""",
    "deployment": """\
# Deployment — C# / ASP.NET Core

## Server
- Kestrel is the default web server. Configure in Program.cs or \
appsettings.json.
- Use reverse proxy (nginx, YARP) in production for TLS termination.
- Enable health checks: `app.MapHealthChecks("/health")`.

## Docker
```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY *.sln ./
COPY src/*/*.csproj ./
RUN for f in *.csproj; do mkdir -p "src/$(basename $f .csproj)" && \
    mv "$f" "src/$(basename $f .csproj)/"; done
RUN dotnet restore
COPY . .
RUN dotnet publish src/MyApp.Api -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /app
COPY --from=build /app/publish .
EXPOSE 8080
ENTRYPOINT ["dotnet", "MyApp.Api.dll"]
```

## Production
- Use `dotnet publish -c Release` for optimized builds.
- Set `ASPNETCORE_ENVIRONMENT=Production` in production.
- Configure connection strings via environment variables or secrets.
- Enable response compression and caching middleware.

## Environment
- `ASPNETCORE_ENVIRONMENT` — environment (Development, Production).
- `ASPNETCORE_URLS` — listen URLs (default http://+:8080).
- `ConnectionStrings__DefaultConnection` — database connection string.
- `DOTNET_RUNNING_IN_CONTAINER=true` — container-aware defaults.\
""",
}
