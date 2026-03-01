"""Spring Boot framework template content."""

CONTENT: dict = {
    "rules": """\
## Framework Rules (Java / Spring Boot)
- Use @RestController for API endpoints, @Service for business logic, \
@Repository for data access. Never put business logic in controllers.
- Use constructor injection (not field injection with @Autowired). All \
dependencies should be final fields assigned via constructor.
- Use DTOs for API request/response bodies. Never expose entity objects \
directly in API responses.
- Validate input with @Valid and Jakarta Bean Validation annotations \
(@NotNull, @Size, @Email). Return 400 with structured error responses.
- Use Spring profiles (application-{profile}.yml) for environment-specific \
configuration. Never hardcode connection strings or secrets.
- Follow the Options pattern: bind config sections to @ConfigurationProperties \
POJOs. Access config through injected beans, not @Value on every field.
- Use ResponseEntity for explicit HTTP status codes. Return 201 for \
creates, 204 for deletes, 422 for validation failures.\
""",
    "architecture": """\
# Architecture — Java / Spring Boot

## Directory Layout
```
src/main/java/com/example/
  config/
    SecurityConfig.java       # Security, CORS, filter chains
    WebConfig.java            # MVC configuration
  controller/
    UserController.java       # @RestController — HTTP endpoints
  service/
    UserService.java          # @Service — business logic
  repository/
    UserRepository.java       # @Repository — JPA data access
  model/
    User.java                 # @Entity — JPA entity
  dto/
    UserRequest.java          # Request DTO with validation
    UserResponse.java         # Response DTO
  exception/
    GlobalExceptionHandler.java  # @ControllerAdvice error handling
src/main/resources/
  application.yml             # Main configuration
  application-dev.yml         # Dev profile overrides
  application-prod.yml        # Production profile
  db/migration/               # Flyway migrations (V1__init.sql)
src/test/java/com/example/
  controller/
    UserControllerTest.java   # @WebMvcTest — slice tests
  service/
    UserServiceTest.java      # Unit tests with Mockito
  repository/
    UserRepositoryTest.java   # @DataJpaTest — repository tests
  integration/
    UserIntegrationTest.java  # @SpringBootTest — full stack
```

## Key Patterns
- **Layered architecture**: Controller → Service → Repository. Each \
layer depends only on the layer below.
- **Exception handling**: @ControllerAdvice with @ExceptionHandler \
methods for consistent error responses.
- **Database migrations**: Flyway or Liquibase for versioned schema \
changes. Never use hibernate auto-DDL in production.
- **Pagination**: use Pageable parameters with Page<T> return types \
for list endpoints.
- **Profiles**: dev (H2 in-memory), test (Testcontainers), prod \
(external PostgreSQL).\
""",
    "conventions": """\
# Conventions — Java / Spring Boot

## Naming
- Classes: PascalCase (`UserController`, `OrderService`).
- Methods: camelCase (`findByEmail`, `createUser`).
- Packages: lowercase dot-separated (`com.example.service`).
- DTOs: `{Entity}Request`, `{Entity}Response`.
- Interfaces: no I-prefix (Java convention). `UserRepository` not \
`IUserRepository`.

## Controller Guidelines
- One resource per controller. Use @RequestMapping for base path.
- Use @GetMapping, @PostMapping, @PutMapping, @DeleteMapping.
- Return ResponseEntity<T> for explicit status control.
- Use @PathVariable for resource IDs, @RequestBody for payloads.
- Keep controllers thin — delegate to services immediately.

## Service Guidelines
- @Transactional on service methods that modify data.
- Throw custom exceptions (ResourceNotFoundException, etc.) — \
let @ControllerAdvice handle HTTP mapping.
- Return domain objects or DTOs, never Optional.empty() for \
expected failures.

## Code Style
- Prefer records for DTOs (Java 16+) or Lombok @Data for older versions.
- Use Optional only for return types, never for parameters or fields.
- Prefer streams and method references over manual loops.
- Follow Google Java Style Guide. Enforce with Checkstyle.\
""",
    "testing": """\
# Testing — Java / Spring Boot

## Stack
- **Framework**: JUnit 5 (@Test, @DisplayName, @Nested).
- **Spring Boot**: @SpringBootTest (full), @WebMvcTest (MVC slice), \
@DataJpaTest (JPA slice).
- **Mocking**: Mockito (@MockBean, @Mock, when/verify).
- **Assertions**: AssertJ (assertThat) preferred over JUnit assertions.
- **Integration**: Testcontainers for real database tests.

## Principles
- Use test slices (@WebMvcTest, @DataJpaTest) over @SpringBootTest \
when possible — faster startup, focused scope.
- MockMvc for controller tests: test request/response without starting \
a server. Verify status codes, JSON paths, headers.
- @MockBean to replace service dependencies in controller slice tests.
- Testcontainers for repository tests that need real SQL behavior.

## File Layout
```
src/test/java/com/example/
  controller/
    UserControllerTest.java   # @WebMvcTest slice tests
  service/
    UserServiceTest.java      # Pure unit tests with @Mock
  repository/
    UserRepositoryTest.java   # @DataJpaTest with Testcontainers
  integration/
    UserFlowTest.java         # @SpringBootTest end-to-end
```

## Commands
- `./mvnw test` — run all tests.
- `./mvnw test -pl module-name` — run tests in a specific module.
- `./mvnw test -Dtest=UserControllerTest` — run single test class.
- `./mvnw test -Dtest=UserControllerTest#testCreate` — single method.
- `./mvnw verify` — run tests + integration tests.\
""",
    "deployment": """\
# Deployment — Java / Spring Boot

## Server
- Spring Boot embeds Tomcat/Netty. No external app server needed.
- Configure server.port, connection pools, and thread counts in \
application.yml.
- Enable Spring Boot Actuator for /health, /info, /metrics endpoints.

## Docker
```dockerfile
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /app
COPY .mvn/ .mvn/
COPY mvnw pom.xml ./
RUN ./mvnw dependency:go-offline -B
COPY src/ src/
RUN ./mvnw package -DskipTests -B

FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

## Production
- Use Spring profiles: `SPRING_PROFILES_ACTIVE=prod`.
- Configure connection pooling with HikariCP (default in Spring Boot).
- Enable graceful shutdown: `server.shutdown=graceful`.
- Set JVM memory: `-Xms512m -Xmx512m` (match container limits).

## Environment
- `SPRING_DATASOURCE_URL` — JDBC connection string.
- `SPRING_DATASOURCE_USERNAME` / `PASSWORD` — database credentials.
- `SPRING_PROFILES_ACTIVE` — active profile (dev, prod).
- `SERVER_PORT` — HTTP port (default 8080).
- `JAVA_OPTS` — JVM flags.\
""",
}
