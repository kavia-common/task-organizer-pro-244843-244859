from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


TaskStatus = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Task title.")
    description: Optional[str] = Field(None, max_length=5000, description="Task description.")
    status: TaskStatus = Field("todo", description="Task status.")
    priority: TaskPriority = Field("medium", description="Task priority.")
    due_date: Optional[date] = Field(None, description="Due date (YYYY-MM-DD).")


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Task title.")
    description: Optional[str] = Field(None, max_length=5000, description="Task description.")
    status: Optional[TaskStatus] = Field(None, description="Task status.")
    priority: Optional[TaskPriority] = Field(None, description="Task priority.")
    due_date: Optional[date] = Field(None, description="Due date (YYYY-MM-DD).")


class TaskResponse(BaseModel):
    id: str = Field(..., description="Task UUID.")
    user_id: str = Field(..., description="Owner user UUID.")
    title: str = Field(..., description="Task title.")
    description: Optional[str] = Field(None, description="Task description.")
    status: TaskStatus = Field(..., description="Task status.")
    priority: TaskPriority = Field(..., description="Task priority.")
    due_date: Optional[date] = Field(None, description="Due date (YYYY-MM-DD).")
    created_at: str = Field(..., description="ISO timestamp when created.")
    updated_at: str = Field(..., description="ISO timestamp when updated.")
