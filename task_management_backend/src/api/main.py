from datetime import date
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.api.deps import get_conn, get_current_user
from src.core.config import get_settings
from src.core.security import create_access_token
from src.db.migrate import run_migrations
from src.models.auth import LoginRequest, SignUpRequest, TokenResponse, UserResponse
from src.models.tasks import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from src.repos.tasks import TasksRepo
from src.repos.users import UsersRepo

openapi_tags = [
    {"name": "Health", "description": "Service health and basic info."},
    {"name": "Auth", "description": "User sign up and login (JWT)."},
    {"name": "Tasks", "description": "Task CRUD + filtering/search."},
]

app = FastAPI(
    title="Task Organizer Pro API",
    description=(
        "Monolithic FastAPI backend for Task Organizer Pro.\n\n"
        "Authentication uses JWT Bearer tokens:\n"
        "- Sign up: POST /auth/signup\n"
        "- Login: POST /auth/login\n"
        "- Use `Authorization: Bearer <token>` for protected routes.\n"
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if settings.allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=settings.allowed_methods if settings.allowed_methods else ["*"],
    allow_headers=settings.allowed_headers if settings.allowed_headers else ["*"],
    max_age=settings.cors_max_age,
)


@app.on_event("startup")
async def _startup() -> None:
    # Ensure schema exists on startup (idempotent).
    run_migrations()


@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Basic health check endpoint.",
)
def health_check():
    # PUBLIC_INTERFACE
    """Health check endpoint.

    Returns:
        JSON message confirming the service is running.
    """
    return {"message": "Healthy"}


@app.get(
    "/docs/auth",
    tags=["Auth"],
    summary="Auth usage help",
    description="Short help text describing how to authenticate against the API.",
    response_class=PlainTextResponse,
)
def auth_docs():
    # PUBLIC_INTERFACE
    """Return instructions on using JWT auth with this API."""
    return (
        "1) POST /auth/signup with {email,password}\n"
        "2) POST /auth/login with {email,password} -> {access_token}\n"
        "3) Call protected endpoints with header:\n"
        "   Authorization: Bearer <access_token>\n"
    )


@app.post(
    "/auth/signup",
    tags=["Auth"],
    summary="Create a new user",
    description="Registers a new user account. Email must be unique.",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(payload: SignUpRequest, conn=Depends(get_conn)):
    # PUBLIC_INTERFACE
    """Register a new user and return basic user info."""
    repo = UsersRepo(conn)
    existing = repo.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = repo.create(email=payload.email, password=payload.password)
    return UserResponse(id=str(user["id"]), email=user["email"], created_at=user["created_at"].isoformat())


@app.post(
    "/auth/register",
    tags=["Auth"],
    summary="Create a new user (alias)",
    description="Alias for POST /auth/signup for compatibility with some clients.",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: SignUpRequest, conn=Depends(get_conn)):
    # PUBLIC_INTERFACE
    """Alias for `signup` to support clients that call /auth/register."""
    return signup(payload=payload, conn=conn)


@app.post(
    "/auth/login",
    tags=["Auth"],
    summary="Login",
    description="Authenticates a user and returns a JWT access token.",
    response_model=TokenResponse,
)
def login(payload: LoginRequest, conn=Depends(get_conn)):
    # PUBLIC_INTERFACE
    """Authenticate a user and return a JWT token."""
    repo = UsersRepo(conn)
    user = repo.authenticate(email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(
        subject=str(user["id"]),
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_exp_minutes,
    )
    return TokenResponse(access_token=token, token_type="bearer")


@app.get(
    "/tasks",
    tags=["Tasks"],
    summary="List tasks",
    description="List tasks for the current user with filtering, sorting, and full-text search.",
    response_model=List[TaskResponse],
)
def list_tasks(
    response: Response,
    q: Optional[str] = Query(None, description="Full-text search query (title+description)."),
    status_: Optional[str] = Query(None, alias="status", description="Filter by status: todo|in_progress|done."),
    priority: Optional[str] = Query(None, description="Filter by priority: low|medium|high."),
    due_from: Optional[date] = Query(None, description="Due date >= (YYYY-MM-DD)."),
    due_to: Optional[date] = Query(None, description="Due date <= (YYYY-MM-DD)."),
    sort: str = Query("created_at", description="Sort field: created_at|updated_at|due_date|priority|status|title."),
    order: str = Query("desc", description="Sort order: asc|desc."),
    limit: int = Query(50, ge=1, le=200, description="Page size."),
    offset: int = Query(0, ge=0, description="Offset for pagination."),
    user=Depends(get_current_user),
    conn=Depends(get_conn),
):
    # PUBLIC_INTERFACE
    """List tasks for the authenticated user."""
    repo = TasksRepo(conn)
    rows, total = repo.list(
        user_id=str(user["id"]),
        q=q,
        status=status_,
        priority=priority,
        due_from=due_from,
        due_to=due_to,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )
    response.headers["X-Total-Count"] = str(total)
    return [
        TaskResponse(
            id=str(r["id"]),
            user_id=str(r["user_id"]),
            title=r["title"],
            description=r.get("description"),
            status=r["status"],
            priority=r["priority"],
            due_date=r.get("due_date"),
            created_at=r["created_at"].isoformat(),
            updated_at=r["updated_at"].isoformat(),
        )
        for r in rows
    ]


@app.post(
    "/tasks",
    tags=["Tasks"],
    summary="Create a task",
    description="Create a new task for the current user.",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(payload: TaskCreateRequest, user=Depends(get_current_user), conn=Depends(get_conn)):
    # PUBLIC_INTERFACE
    """Create a task belonging to the authenticated user."""
    repo = TasksRepo(conn)
    task = repo.create(
        user_id=str(user["id"]),
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    return TaskResponse(
        id=str(task["id"]),
        user_id=str(task["user_id"]),
        title=task["title"],
        description=task.get("description"),
        status=task["status"],
        priority=task["priority"],
        due_date=task.get("due_date"),
        created_at=task["created_at"].isoformat(),
        updated_at=task["updated_at"].isoformat(),
    )


@app.get(
    "/tasks/{task_id}",
    tags=["Tasks"],
    summary="Get a task",
    description="Get a single task by id (must belong to the current user).",
    response_model=TaskResponse,
)
def get_task(task_id: str, user=Depends(get_current_user), conn=Depends(get_conn)):
    # PUBLIC_INTERFACE
    """Get a task by id for the authenticated user."""
    repo = TasksRepo(conn)
    task = repo.get(user_id=str(user["id"]), task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=str(task["id"]),
        user_id=str(task["user_id"]),
        title=task["title"],
        description=task.get("description"),
        status=task["status"],
        priority=task["priority"],
        due_date=task.get("due_date"),
        created_at=task["created_at"].isoformat(),
        updated_at=task["updated_at"].isoformat(),
    )


@app.patch(
    "/tasks/{task_id}",
    tags=["Tasks"],
    summary="Update a task",
    description="Update fields on a task (must belong to the current user).",
    response_model=TaskResponse,
)
def update_task(task_id: str, payload: TaskUpdateRequest, user=Depends(get_current_user), conn=Depends(get_conn)):
    # PUBLIC_INTERFACE
    """Update a task by id for the authenticated user."""
    repo = TasksRepo(conn)
    fields = payload.model_dump(exclude_unset=True)
    task = repo.update(user_id=str(user["id"]), task_id=task_id, fields=fields)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(
        id=str(task["id"]),
        user_id=str(task["user_id"]),
        title=task["title"],
        description=task.get("description"),
        status=task["status"],
        priority=task["priority"],
        due_date=task.get("due_date"),
        created_at=task["created_at"].isoformat(),
        updated_at=task["updated_at"].isoformat(),
    )


@app.delete(
    "/tasks/{task_id}",
    tags=["Tasks"],
    summary="Delete a task",
    description="Delete a task by id (must belong to the current user).",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(task_id: str, user=Depends(get_current_user), conn=Depends(get_conn)):
    # PUBLIC_INTERFACE
    """Delete a task by id for the authenticated user."""
    repo = TasksRepo(conn)
    deleted = repo.delete(user_id=str(user["id"]), task_id=task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
